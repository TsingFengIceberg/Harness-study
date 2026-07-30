#!/usr/bin/env python3
"""Fetch the JavaGuide AI sidebar knowledge base as Markdown."""

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


BASE_URL = "https://javaguide.cn"
INDEX_URL = f"{BASE_URL}/ai/ai-core-concepts.html"
USER_AGENT = "Mozilla/5.0 (compatible; AgentSystemsStudy/1.0)"
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "ai"
GROUPS = {
    "overview": {"sidebar_title": "入门总览", "expected_pages": 1},
    "interview-questions": {"sidebar_title": "面试题", "expected_pages": 5},
    "llm-basis": {"sidebar_title": "大模型基础", "expected_pages": 4},
    "agent": {"sidebar_title": "AI Agent", "expected_pages": 9},
    "rag": {"sidebar_title": "RAG", "expected_pages": 6},
    "system-design": {"sidebar_title": "AI 系统设计", "expected_pages": 3},
}
EXPECTED_TOTAL = 28
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


class SidebarParser(HTMLParser):
    """Extract grouped links from the server-rendered AI sidebar."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_sidebar = False
        self.capture_group = False
        self.capture_link = False
        self.text: list[str] = []
        self.href = ""
        self.groups: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if not self.in_sidebar:
            if tag == "aside" and attr_map.get("id") == "sidebar":
                self.in_sidebar = True
            return
        classes = set(attr_map.get("class", "").split())
        if tag == "span" and "vp-sidebar-title" in classes:
            self.capture_group = True
            self.text = []
        elif tag == "a" and "vp-sidebar-link" in classes:
            self.capture_link = True
            self.text = []
            self.href = attr_map.get("href", "")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_sidebar:
            return
        if tag == "span" and self.capture_group:
            self.groups.append({"title": clean_inline("".join(self.text)), "pages": []})
            self.capture_group = False
            self.text = []
        elif tag == "a" and self.capture_link:
            if not self.groups:
                raise RuntimeError("Sidebar link appeared before its group title")
            pages = self.groups[-1]["pages"]
            assert isinstance(pages, list)
            pages.append(
                {
                    "sidebar_title": clean_inline("".join(self.text)),
                    "url": urljoin(BASE_URL, self.href),
                }
            )
            self.capture_link = False
            self.text = []
        elif tag == "aside":
            self.in_sidebar = False

    def handle_data(self, data: str) -> None:
        if self.capture_group or self.capture_link:
            self.text.append(data)


class PageTitleParser(HTMLParser):
    """Extract the first H1, which JavaGuide renders outside article content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.capture = False
        self.done = False
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h1" and not self.done:
            self.capture = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self.capture:
            self.capture = False
            self.done = True

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.text.append(data)


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


def extract_document_title(document: str, url: str) -> str:
    parser = PageTitleParser()
    parser.feed(document)
    title = clean_inline("".join(parser.text))
    if not title:
        raise RuntimeError(f"Missing page H1 in {url}")
    return title


def local_path_for_url(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.netloc != urlparse(BASE_URL).netloc:
        raise RuntimeError(f"Unexpected JavaGuide host in {url}")
    if not parsed.path.startswith("/ai/") or not parsed.path.endswith(".html"):
        raise RuntimeError(f"Unexpected JavaGuide AI path in {url}")
    return Path(parsed.path.removeprefix("/ai/")).with_suffix(".md")


def parse_sidebar(document: str) -> list[dict[str, object]]:
    parser = SidebarParser()
    parser.feed(document)
    expected_titles = [str(config["sidebar_title"]) for config in GROUPS.values()]
    found_titles = [str(group["title"]) for group in parser.groups]
    if found_titles != expected_titles:
        raise RuntimeError(
            f"Expected sidebar groups {expected_titles}, found {found_titles}"
        )

    total = 0
    for (slug, config), group in zip(GROUPS.items(), parser.groups):
        pages = group["pages"]
        assert isinstance(pages, list)
        expected_pages = int(config["expected_pages"])
        group_title = str(group["title"])
        if len(pages) != expected_pages:
            raise RuntimeError(
                f"Expected {expected_pages} pages in {group_title}, found {len(pages)}"
            )
        group["slug"] = slug
        for page in pages:
            assert isinstance(page, dict)
            page["local_path"] = local_path_for_url(str(page["url"]))
        total += len(pages)

    if total != EXPECTED_TOTAL:
        raise RuntimeError(f"Expected {EXPECTED_TOTAL} sidebar pages, found {total}")
    return parser.groups


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
    return markdown.strip() + "\n"


def article_index_link(local_path: Path) -> str:
    return "../" * (len(local_path.parent.parts) + 1) + "README.md"


def page_document(
    title: str,
    source_url: str,
    body: str,
    retrieved: str,
    index_link: str,
    previous_link: tuple[str, str] | None,
    next_link: tuple[str, str] | None,
) -> str:
    related = [f"[返回 JavaGuide 本地索引]({index_link})"]
    if previous_link:
        related.append(f"[上一篇：{previous_link[0]}]({previous_link[1]})")
    if next_link:
        related.append(f"[下一篇：{next_link[0]}]({next_link[1]})")
    navigation = " / ".join(related)
    return normalize_markdown(
        f"# {title}\n\n"
        f"> **来源**: [{source_url}]({source_url})  \n"
        f"> **抓取日期**: {retrieved}  \n"
        f"> **资料性质**: JavaGuide 第三方网页机械提取  \n"
        f"> **证据状态**: to-verify\n\n"
        f"{navigation}\n\n"
        f"---\n\n"
        f"{body}"
    )


def index_document(groups: list[dict[str, object]], retrieved: str) -> str:
    sections: list[str] = []
    for group in groups:
        group_title = str(group["title"])
        pages = group["pages"]
        assert isinstance(pages, list)
        rows = [
            "| 标题 | 本地提取稿 | 原始网页 |",
            "|---|---|---|",
        ]
        for page in pages:
            assert isinstance(page, dict)
            page_title = str(page["sidebar_title"])
            url = str(page["url"])
            local_path = Path(page["local_path"])
            rows.append(
                f"| {page_title} | [ai/{local_path.as_posix()}](ai/{local_path.as_posix()}) | "
                f"[source]({url}) |"
            )
        sections.append(f"## {group_title}\n\n" + "\n".join(rows))

    return normalize_markdown(
        "# JavaGuide AI Knowledge Base\n\n"
        f"> **来源站点**: [JavaGuide AI 应用开发]({INDEX_URL})  \n"
        f"> **抓取日期**: {retrieved}  \n"
        "> **资料性质**: 第三方网页机械提取  \n"
        "> **证据状态**: to-verify\n\n"
        "本目录是独立的 JavaGuide AI 知识库镜像，不属于 Xiaolin 面试资料。"
        "当前保存左侧 AI 侧栏的 6 个分组、28 个页面，用于本地全文搜索、课程定位和来源对照。"
        "网页内容不是本仓库的已核验结论；涉及框架行为、版本、性能数字和工程判断时，"
        "仍需回到源码或官方资料核验。\n\n"
        "转换保留标题、正文、列表、表格、代码块、链接和远程图片 URL，图片文件本身未下载。"
        "少量客户端动态图在服务端 HTML 中只有“图表加载中”占位，提取稿会如实保留；"
        "需要查看图形时应回到原始网页。重新抓取全部页面可运行：\n\n"
        "```bash\n"
        "python3 references/agent-interview/javaguide/scripts/fetch-javaguide-ai.py\n"
        "```\n\n"
        "也可以在命令后指定 `overview`、`interview-questions`、`llm-basis`、`agent`、`rag` 或 "
        "`system-design`，只刷新部分侧栏分组。\n\n"
        + "\n\n".join(sections)
        + "\n"
    )


def write_group(
    group: dict[str, object],
    retrieved: str,
    cached_documents: dict[str, str],
) -> None:
    pages = group["pages"]
    assert isinstance(pages, list)
    for index, page in enumerate(pages):
        assert isinstance(page, dict)
        if index:
            time.sleep(0.5)
        url = str(page["url"])
        document = cached_documents.get(url)
        if document is None:
            document = fetch(url)
        title = extract_document_title(document, url)
        root = parse_article(document, url)
        body = normalize_markdown(MarkdownRenderer(url).render(root))
        local_path = Path(page["local_path"])
        output_path = OUTPUT_ROOT / local_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        previous_link = None
        if index:
            previous = pages[index - 1]
            assert isinstance(previous, dict)
            previous_path = Path(previous["local_path"])
            previous_link = (str(previous["sidebar_title"]), previous_path.name)

        next_link = None
        if index + 1 < len(pages):
            following = pages[index + 1]
            assert isinstance(following, dict)
            following_path = Path(following["local_path"])
            next_link = (str(following["sidebar_title"]), following_path.name)

        output_path.write_text(
            page_document(
                title,
                url,
                body,
                retrieved,
                article_index_link(local_path),
                previous_link,
                next_link,
            ),
            encoding="utf-8",
        )
    group_slug = str(group["slug"])
    print(f"Wrote {len(pages)} pages for {group_slug}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "groups",
        nargs="*",
        choices=sorted(GROUPS),
        default=None,
        help="sidebar groups to fetch; defaults to all groups",
    )
    args = parser.parse_args()
    retrieved = date.today().isoformat()
    index_html = fetch(INDEX_URL)
    groups = parse_sidebar(index_html)

    index_path = SCRIPT_DIR.parent / "README.md"
    index_path.write_text(index_document(groups, retrieved), encoding="utf-8")

    selected = args.groups or list(GROUPS)
    groups_by_slug = {str(group["slug"]): group for group in groups}
    cached_documents = {INDEX_URL: index_html}
    for index, slug in enumerate(selected):
        if index:
            time.sleep(0.5)
        write_group(groups_by_slug[slug], retrieved, cached_documents)


if __name__ == "__main__":
    main()
