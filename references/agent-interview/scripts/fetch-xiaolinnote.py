#!/usr/bin/env python3
"""Fetch Xiaolin AI interview indexes and chapters as Markdown."""

from __future__ import annotations

import argparse
import html
import re
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from html.parser import HTMLParser


BASE_URL = "https://xiaolinnote.com"
USER_AGENT = "Mozilla/5.0 (compatible; AgentSystemsStudy/1.0)"
SCRIPT_DIR = Path(__file__).resolve().parent
SECTIONS = {
    "agent": {
        "index_stem": "agent_info",
        "expected_chapters": 16,
        "numbered": True,
        "display_name": "Agent Interview Notes",
    },
    "rag": {
        "index_stem": "rag_info",
        "expected_chapters": 20,
        "numbered": True,
        "display_name": "RAG Interview Notes",
    },
    "tools": {
        "index_stem": "tools_info",
        "expected_chapters": 16,
        "numbered": True,
        "display_name": "LLM Tool Calling Interview Notes",
    },
    "llm": {
        "index_stem": "llm_info",
        "expected_chapters": 22,
        "numbered": False,
        "display_name": "LLM Engineering Interview Notes",
    },
}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[Node | str] = field(default_factory=list)


class ArticleParser(HTMLParser):
    """Build a small DOM for the server-rendered #markdown-content element."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: Node | None = None
        self.stack: list[Node] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if not self.stack:
            if tag == "div" and attr_map.get("id") == "markdown-content":
                self.root = Node(tag, attr_map)
                self.stack.append(self.root)
            return

        node = Node(tag, attr_map)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self.stack:
            self.stack[-1].children.append(data)


def fetch(url: str, attempts: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=30) as response:
                content_type = response.headers.get("Content-Type", "")
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} for {url}")
                if "text/html" not in content_type:
                    raise RuntimeError(f"Unexpected content type {content_type!r} for {url}")
                return response.read().decode("utf-8", "replace")
        except Exception as exc:  # urllib raises several transport-specific errors.
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def parse_article(document: str, url: str) -> Node:
    parser = ArticleParser()
    parser.feed(document)
    if parser.root is None:
        raise RuntimeError(f"Missing #markdown-content in {url}")
    return parser.root


def iter_nodes(node: Node) -> Iterable[Node]:
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from iter_nodes(child)


def plain_text(node: Node | str, preserve_whitespace: bool = False) -> str:
    if isinstance(node, str):
        return node if preserve_whitespace else re.sub(r"\s+", " ", node)
    return "".join(plain_text(child, preserve_whitespace) for child in node.children)


def discover_chapters(
    root: Node,
    section: str,
    index_stem: str,
    expected_chapters: int,
    numbered: bool,
) -> list[tuple[int, str]]:
    pattern = re.compile(rf"^/ai/{re.escape(section)}/([a-z0-9_]+)\.html$")
    discovered: list[str] = []
    for node in iter_nodes(root):
        if node.tag != "a":
            continue
        href = node.attrs.get("href", "")
        parsed = urlparse(urljoin(BASE_URL, href))
        match = pattern.match(parsed.path)
        if not match or match.group(1) == index_stem:
            continue
        url = urljoin(BASE_URL, parsed.path)
        if url not in discovered:
            discovered.append(url)

    if numbered:
        found: dict[int, str] = {}
        numbered_pattern = re.compile(r"^(\d+)_[a-z0-9_]+$")
        for url in discovered:
            match = numbered_pattern.match(Path(urlparse(url).path).stem)
            if match:
                found[int(match.group(1))] = url
        expected = list(range(1, expected_chapters + 1))
        if sorted(found) != expected:
            raise RuntimeError(
                f"Expected {section} chapter numbers {expected}, found {sorted(found)}"
            )
        return sorted(found.items())

    if len(discovered) != expected_chapters:
        raise RuntimeError(
            f"Expected {expected_chapters} {section} chapters, found {len(discovered)}"
        )
    return list(enumerate(discovered, start=1))


def escape_inline(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|")


def clean_inline(text: str) -> str:
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", " ", text)
    text = re.sub(r" +([，。！？；：、,.!?;:)])", r"\1", text)
    text = re.sub(r"([(]) +", r"\1", text)
    return text.strip()


def code_fence(content: str) -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", content)), default=0)
    return "`" * max(1, longest + 1)


class MarkdownRenderer:
    def __init__(self, page_url: str) -> None:
        self.page_url = page_url

    def render(self, node: Node | str, *, inline: bool = False) -> str:
        if isinstance(node, str):
            return re.sub(r"\s+", " ", html.unescape(node))

        tag = node.tag
        if tag in {"script", "style", "svg", "button"}:
            return ""
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            return f"{'#' * level} {clean_inline(plain_text(node))}\n\n"
        if tag == "p":
            content = clean_inline(self.render_children(node, inline=True))
            return f"{content}\n\n" if content else ""
        if tag in {"strong", "b"}:
            content = clean_inline(self.render_children(node, inline=True))
            return f"**{content}**" if content else ""
        if tag in {"em", "i"}:
            content = clean_inline(self.render_children(node, inline=True))
            return f"*{content}*" if content else ""
        if tag == "del":
            content = clean_inline(self.render_children(node, inline=True))
            return f"~~{content}~~" if content else ""
        if tag == "br":
            return "  \n"
        if tag == "hr":
            return "\n---\n\n"
        if tag == "a":
            content = clean_inline(self.render_children(node, inline=True))
            href = node.attrs.get("href", "")
            if not href:
                return content
            target = urljoin(self.page_url, href)
            return f"[{content}]({target})" if content else target
        if tag == "img":
            src = node.attrs.get("src", "")
            if not src:
                return ""
            alt = clean_inline(node.attrs.get("alt", ""))
            return f"![{alt}]({urljoin(self.page_url, src)})"
        if tag == "code":
            content = plain_text(node, preserve_whitespace=True).strip("\n")
            fence = code_fence(content)
            return f"{fence}{content}{fence}"
        if tag == "pre":
            content = plain_text(node, preserve_whitespace=True).strip("\n")
            language = self.code_language(node)
            fence = "`" * max(3, code_fence(content).__len__())
            return f"\n{fence}{language}\n{content}\n{fence}\n\n"
        if tag in {"ul", "ol"}:
            return self.render_list(node, ordered=tag == "ol") + "\n"
        if tag == "li":
            return clean_inline(self.render_children(node, inline=True))
        if tag == "blockquote":
            content = self.render_children(node).strip()
            return "\n".join(f"> {line}" if line else ">" for line in content.splitlines()) + "\n\n"
        if tag == "table":
            return self.render_table(node)
        if tag == "figure":
            content = self.render_children(node).strip()
            return f"{content}\n\n" if content else ""
        if tag == "figcaption":
            content = clean_inline(self.render_children(node, inline=True))
            return f"*{content}*\n\n" if content else ""
        if tag == "summary":
            content = clean_inline(self.render_children(node, inline=True))
            return f"**{content}**\n\n" if content else ""

        content = self.render_children(node, inline=inline)
        if tag in {"div", "section", "article", "details"} and content.strip():
            return content + ("" if content.endswith("\n") else "\n")
        return content

    def render_children(self, node: Node, *, inline: bool = False) -> str:
        return "".join(self.render(child, inline=inline) for child in node.children)

    def render_list(self, node: Node, *, ordered: bool) -> str:
        lines: list[str] = []
        index = 1
        for child in node.children:
            if not isinstance(child, Node) or child.tag != "li":
                continue
            nested: list[str] = []
            body_parts: list[str] = []
            for item in child.children:
                if isinstance(item, Node) and item.tag in {"ul", "ol"}:
                    nested.append(self.render_list(item, ordered=item.tag == "ol").rstrip())
                else:
                    body_parts.append(self.render(item, inline=True))
            marker = f"{index}." if ordered else "-"
            body = clean_inline("".join(body_parts))
            lines.append(f"{marker} {body}".rstrip())
            for nested_block in nested:
                lines.extend(f"  {line}" for line in nested_block.splitlines())
            index += 1
        return "\n".join(lines) + ("\n" if lines else "")

    def render_table(self, node: Node) -> str:
        rows: list[list[str]] = []
        header_flags: list[bool] = []
        for row in (item for item in iter_nodes(node) if item.tag == "tr"):
            cells: list[str] = []
            has_header = False
            for cell in row.children:
                if isinstance(cell, Node) and cell.tag in {"th", "td"}:
                    has_header = has_header or cell.tag == "th"
                    value = clean_inline(self.render_children(cell, inline=True))
                    cells.append(escape_inline(value))
            if cells:
                rows.append(cells)
                header_flags.append(has_header)
        if not rows:
            return ""
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        header = rows[0]
        output = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in range(width)) + " |",
        ]
        for row in rows[1:]:
            output.append("| " + " | ".join(row) + " |")
        return "\n".join(output) + "\n\n"

    @staticmethod
    def code_language(node: Node) -> str:
        for item in iter_nodes(node):
            if item.tag != "code":
                continue
            classes = item.attrs.get("class", "").split()
            for class_name in classes:
                if class_name.startswith("language-"):
                    return class_name.removeprefix("language-")
        return ""


def normalize_markdown(markdown: str) -> str:
    markdown = markdown.replace("\u00a0", " ")
    markdown = re.sub(r"\n[ \t]+\n", "\n\n", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(
        r"\n(?:---\n\n)?对了，[^\n]*公众号@小林面试笔记题.*\Z",
        "\n",
        markdown,
        flags=re.DOTALL,
    )
    return markdown.strip() + "\n"


def extract_title(root: Node, url: str) -> str:
    for node in iter_nodes(root):
        if node.tag == "h1":
            title = clean_inline(plain_text(node))
            if title:
                return title
    raise RuntimeError(f"Missing article title in {url}")


def remove_first_h1(markdown: str) -> str:
    return re.sub(r"^# .+?\n+", "", markdown, count=1)


def chapter_filename(number: int, url: str, numbered: bool) -> str:
    stem = Path(urlparse(url).path).stem
    if numbered:
        stem = stem.split("_", 1)[1]
    slug = stem.replace("_", "-")
    return f"{number:02d}-{slug}.md"


def page_document(
    title: str,
    source_url: str,
    body: str,
    retrieved: str,
    previous_link: tuple[str, str] | None,
    next_link: tuple[str, str] | None,
) -> str:
    related: list[str] = ["[返回本地索引](README.md)"]
    if previous_link:
        related.append(f"[上一章：{previous_link[0]}]({previous_link[1]})")
    if next_link:
        related.append(f"[下一章：{next_link[0]}]({next_link[1]})")
    return normalize_markdown(
        f"# {title}\n\n"
        f"> **来源**: [{source_url}]({source_url})  \n"
        f"> **抓取日期**: {retrieved}  \n"
        f"> **资料性质**: 第三方网页机械提取  \n"
        f"> **证据状态**: to-verify\n\n"
        f"{' / '.join(related)}\n\n"
        f"---\n\n"
        f"{remove_first_h1(body)}"
    )


def index_document(
    entry_title: str,
    entry_filename: str,
    chapters: list[dict[str, str | int]],
    retrieved: str,
    index_url: str,
    display_name: str,
) -> str:
    rows = [
        "| 序号 | 标题 | 本地提取稿 | 原始网页 |",
        "|---:|---|---|---|",
        f"| 0 | {entry_title} | [{entry_filename}]({entry_filename}) | [source]({index_url}) |",
    ]
    for chapter in chapters:
        rows.append(
            f"| {chapter['number']} | {chapter['title']} | "
            f"[{chapter['filename']}]({chapter['filename']}) | "
            f"[source]({chapter['url']}) |"
        )
    return normalize_markdown(
        f"# Xiaolin {display_name}\n\n"
        f"> **来源站点**: [小林面试笔记]({index_url})  \n"
        f"> **抓取日期**: {retrieved}  \n"
        "> **资料性质**: 第三方网页机械提取  \n"
        "> **证据状态**: to-verify\n\n"
        f"本目录保存“{entry_title}”入口页和 {len(chapters)} 个子页的结构化 Markdown 提取稿，"
        "用于本地全文搜索、课程定位和问题目录整理。网页内容不是本仓库的已核验结论；"
        "涉及框架、协议、论文、版本和工程判断时，仍需回到源码或官方资料核验。\n\n"
        "转换保留标题、正文、列表、表格、代码块、链接和远程图片 URL；重复的站点推广尾部已移除，"
        "图片文件本身未下载。重新抓取可运行 "
        "[`../../scripts/fetch-xiaolinnote.py`](../../scripts/fetch-xiaolinnote.py)。\n\n"
        "## 章节目录\n\n"
        + "\n".join(rows)
        + "\n"
    )


def fetch_section(section: str, config: dict[str, object], retrieved: str) -> None:
    index_stem = str(config["index_stem"])
    expected_chapters = int(config["expected_chapters"])
    numbered = bool(config["numbered"])
    display_name = str(config["display_name"])
    index_url = f"{BASE_URL}/ai/{section}/{index_stem}.html"
    output_dir = SCRIPT_DIR.parent / "xiaolinnote" / section
    output_dir.mkdir(parents=True, exist_ok=True)

    entry_html = fetch(index_url)
    entry_root = parse_article(entry_html, index_url)
    discovered = discover_chapters(
        entry_root,
        section,
        index_stem,
        expected_chapters,
        numbered,
    )

    pages: list[dict[str, str | int]] = []
    for index, (number, url) in enumerate(discovered):
        if index:
            time.sleep(0.5)
        document = fetch(url)
        root = parse_article(document, url)
        title = extract_title(root, url)
        body = normalize_markdown(MarkdownRenderer(url).render(root))
        pages.append(
            {
                "number": number,
                "url": url,
                "title": title,
                "filename": chapter_filename(number, url, numbered),
                "body": body,
            }
        )

    entry_title = extract_title(entry_root, index_url)
    entry_body = normalize_markdown(MarkdownRenderer(index_url).render(entry_root))
    entry_filename = f"00-{section}-interview-guide.md"
    first_page = pages[0]
    (output_dir / entry_filename).write_text(
        page_document(
            entry_title,
            index_url,
            entry_body,
            retrieved,
            None,
            (str(first_page["title"]), str(first_page["filename"])),
        ),
        encoding="utf-8",
    )

    for index, page in enumerate(pages):
        previous = pages[index - 1] if index else None
        following = pages[index + 1] if index + 1 < len(pages) else None
        previous_link = (
            (str(previous["title"]), str(previous["filename"]))
            if previous
            else (entry_title, entry_filename)
        )
        next_link = (
            (str(following["title"]), str(following["filename"]))
            if following
            else None
        )
        (output_dir / str(page["filename"])).write_text(
            page_document(
                str(page["title"]),
                str(page["url"]),
                str(page["body"]),
                retrieved,
                previous_link,
                next_link,
            ),
            encoding="utf-8",
        )

    (output_dir / "README.md").write_text(
        index_document(
            entry_title,
            entry_filename,
            pages,
            retrieved,
            index_url,
            display_name,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(pages) + 2} Markdown files to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "sections",
        nargs="*",
        choices=sorted(SECTIONS),
        default=None,
        help="sections to fetch; defaults to all sections",
    )
    args = parser.parse_args()
    retrieved = date.today().isoformat()
    sections = args.sections or list(SECTIONS)
    for index, section in enumerate(sections):
        if index:
            time.sleep(0.5)
        fetch_section(section, SECTIONS[section], retrieved)

if __name__ == "__main__":
    main()
