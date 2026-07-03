#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import markdown

# Programmatically set the library path so WeasyPrint can find Cairo/Pango on macOS (Homebrew)
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

try:
    from weasyprint import HTML
except OSError as e:
    print(f"Error importing WeasyPrint: {e}")
    print("Please make sure Pango and Cairo are installed on your system (e.g., brew install pango cairo).")
    sys.exit(1)

def preprocess_markdown(md_text):
    """
    Strips leading spaces from block elements like tables and images
    so that standard markdown doesn'\''t treat them as preformatted code blocks.
    Also ensures there is a blank line before tables and images to help the parser.
    """
    lines = md_text.split("\n")
    processed_lines = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\s*\|", line):
            if not in_table:
                processed_lines.append("")
                in_table = True
            processed_lines.append(stripped)
        elif stripped.startswith("!["):
            in_table = False
            processed_lines.append("") # blank line before image
            processed_lines.append(stripped)
            processed_lines.append("") # blank line after image
        else:
            in_table = False
            processed_lines.append(line)
            
    return "\n".join(processed_lines)

def parse_summary(summary_path):
    """
    Parses SUMMARY.md to get the sorted list of chapter markdown files and their display names.
    """
    chapters = []
    if not os.path.exists(summary_path):
        print(f"Error: {summary_path} not found.")
        sys.exit(1)
        
    with open(summary_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Match lines like: - [北京市自驾游指南](01_北京市.md)
    matches = re.findall(r'-\s+\[([^\]]+)\]\(([^)]+\.md)\)', content)
    for title, filename in matches:
        # Extract number prefix to identify chapter number (e.g., "01" from "01_北京市.md")
        num_match = re.match(r'^(\d+)_', filename)
        if num_match:
            num_str = num_match.group(1)
            chapters.append({
                "num": num_str,
                "title": title.strip(),
                "filename": filename
            })
    return chapters

def main():
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(workspace_dir, "docs")
    summary_path = os.path.join(docs_dir, "SUMMARY.md")
    
    print("Parsing book index...")
    chapters = parse_summary(summary_path)
    print(f"Found {len(chapters)} chapters in SUMMARY.md.")
    
    # 1. Construct the CSS styling
    css_content = """
    @page {
        size: A4;
        margin: 20mm 20mm 20mm 20mm;
        @bottom-center {
            content: counter(page);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 9pt;
            color: #94a3b8;
        }
    }
    
    @page cover-page {
        margin: 0;
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        @bottom-center { content: none; }
    }
    
    @page toc-page {
        margin: 20mm 20mm 20mm 20mm;
        @bottom-center { content: none; }
    }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
        line-height: 1.7;
        color: #334155;
        font-size: 11pt;
    }
    
    /* Cover Page */
    .cover {
        page: cover-page;
        height: 297mm;
        width: 210mm;
        box-sizing: border-box;
        padding: 90mm 20mm 20mm 20mm;
        color: #ffffff;
        text-align: center;
        break-after: page;
    }
    .cover h1 {
        font-size: 42pt;
        font-weight: 800;
        letter-spacing: 6px;
        margin: 0 0 10px 0;
        color: #ffffff;
        border-bottom: none;
        padding-bottom: 0;
        text-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
    }
    .cover .divider {
        width: 90mm;
        height: 3px;
        background: linear-gradient(90deg, transparent, #60a5fa, transparent);
        margin: 20px auto;
    }
    .cover h2 {
        font-size: 20pt;
        font-weight: 300;
        letter-spacing: 3px;
        color: #93c5fd;
        border: none;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .cover .author {
        font-size: 14pt;
        color: #94a3b8;
        margin-top: 80mm;
        letter-spacing: 4px;
        font-weight: 300;
    }
    
    /* Table of Contents */
    .toc-page {
        page: toc-page;
        break-before: page;
        break-after: page;
        padding-top: 10mm;
    }
    .toc-page h1 {
        font-size: 24pt;
        color: #0f172a;
        margin-bottom: 30px;
        border-bottom: 2px solid #1e3a8a;
        padding-bottom: 10px;
        text-align: center;
        break-before: avoid;
    }
    .toc {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .toc li {
        display: flex;
        align-items: baseline;
        margin-bottom: 12px;
        font-size: 11.5pt;
    }
    .toc li a {
        text-decoration: none;
        color: #334155;
        font-weight: 500;
        transition: color 0.2s;
    }
    .toc li a:hover {
        color: #2563eb;
    }
    .toc li .leader {
        flex-grow: 1;
        border-bottom: 1px dotted #cbd5e1;
        margin: 0 10px;
    }
    .toc li .page-ref {
        text-decoration: none;
        color: #1e293b;
        font-weight: bold;
    }
    .toc li .page-ref::after {
        content: target-counter(attr(href), page);
    }
    
    /* Chapters & Layout */
    .chapter {
        break-before: page;
    }
    .chapter:first-of-type {
        counter-reset: page 1;
    }
    
    h1 {
        font-size: 24pt;
        color: #0f172a;
        margin-top: 0;
        margin-bottom: 20px;
        font-weight: 700;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 10px;
        break-before: page;
        string-set: chapter-title content();
    }
    h2 {
        font-size: 16pt;
        color: #1e293b;
        margin-top: 30px;
        margin-bottom: 15px;
        font-weight: 600;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 6px;
        break-after: avoid;
    }
    h3 {
        font-size: 13pt;
        color: #1e3a8a;
        margin-top: 25px;
        margin-bottom: 12px;
        font-weight: 600;
        break-after: avoid;
    }
    p {
        margin-top: 0;
        margin-bottom: 15px;
        text-align: justify;
    }
    strong {
        color: #0f172a;
    }
    
    /* Centered, Non-breaking Images */
    img {
        display: block;
        margin: 20px auto;
        max-width: 95%;
        max-height: 85mm; /* Dynamic height limit to prevent layout overflow */
        width: auto;
        height: auto;
        object-fit: contain;
        border-radius: 6px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
        break-inside: avoid;
        page-break-inside: avoid;
    }
    
    /* Make human geography maps (人文地图) match route maps in width, scaling height proportionally */
    img[alt*="人文地图"] {
        width: 95%;
        max-width: 95%;
        max-height: 160mm; /* Allow more height so square maps can span full page width */
        height: auto;
    }
    
    /* Prevent images/tables in lists from breaking across pages */
    .chapter p {
        break-inside: avoid;
    }
    .chapter ul li {
        break-inside: avoid-page;
        margin-bottom: 8px;
    }
    .chapter ul li ul li {
        break-inside: avoid-page;
        margin-bottom: 4px;
    }
    
    /* Tables design */
    table {
        width: 100%;
        max-width: 98%;
        margin: 20px auto;
        border-collapse: collapse;
        font-size: 10pt;
        break-inside: avoid;
        page-break-inside: avoid;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        border-radius: 6px;
        overflow: hidden;
    }
    th, td {
        padding: 8px 12px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
    }
    th {
        background-color: #1e3a8a;
        color: #ffffff;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 9.5pt;
        letter-spacing: 0.5px;
    }
    tr:nth-child(even) {
        background-color: #f8fafc;
    }
    tr:hover {
        background-color: #f1f5f9;
    }
    """
    
    # 2. Build the HTML content
    print("Compiling chapters into HTML...")
    html_parts = []
    
    # Cover Page HTML
    html_parts.append("""
    <div class="cover">
        <div class="cover-content">
            <h1>追光而行</h1>
            <div class="divider"></div>
            <h2>中国绝美自驾路线规划指南</h2>
            <p class="author">Chasing Horizons</p>
        </div>
    </div>
    """)
    
    # Build Table of Contents HTML
    toc_html = []
    toc_html.append('<div class="toc-page">')
    toc_html.append('<h1>目录</h1>')
    toc_html.append('<ul class="toc">')
    
    # Generate TOC items and load each chapter content
    chapters_html = []
    for chap in chapters:
        # Chapter ID
        chap_id = f"chap-{chap['num']}"
        
        # Parse chapter markdown
        chap_file_path = os.path.join(docs_dir, chap["filename"])
        if not os.path.exists(chap_file_path):
            print(f"Warning: Chapter file {chap_file_path} not found. Skipping.")
            continue
            
        with open(chap_file_path, "r", encoding="utf-8") as f:
            md_text = f.read()
            
        # Preprocess markdown to fix table and image indent/codeblock parsing issues
        md_text = preprocess_markdown(md_text)
            
        # Extract the actual first H1 title from Markdown to make it clean
        h1_match = re.search(r'^#\s+(.+)$', md_text, re.MULTILINE)
        clean_title = h1_match.group(1).strip() if h1_match else chap["title"]
        
        # Add to TOC
        toc_html.append(f'<li><a href="#{chap_id}">{clean_title}</a><span class="leader"></span><a class="page-ref" href="#{chap_id}"></a></li>')
        
        # Convert Markdown to HTML
        chap_html_content = markdown.markdown(md_text, extensions=['tables'])
        
        # Post-process internal links to make them work as PDF anchors
        chap_html_content = re.sub(
            r'href=["\'](?:docs/)?(\d+)_.*?\.md["\']', 
            r'href="#chap-\1"', 
            chap_html_content
        )
        
        # Wrap chapter in a div container
        chapters_html.append(f'<div class="chapter" id="{chap_id}">{chap_html_content}</div>')
        
    toc_html.append('</ul>')
    toc_html.append('</div>')
    
    # Merge all parts
    full_html = f"""<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>追光而行：中国绝美自驾路线规划指南</title>
        <style>
            {css_content}
        </style>
    </head>
    <body>
        {"".join(html_parts)}
        {"".join(toc_html)}
        {"".join(chapters_html)}
    </body>
    </html>
    """
    
    # Write temporary book.html inside the docs directory so image paths resolve relative to it
    html_output_path = os.path.join(docs_dir, "book.html")
    print(f"Writing intermediate HTML file to {html_output_path}...")
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(full_html)
        
    # 3. Generate the PDF
    pdf_output_path = os.path.join(workspace_dir, "ChasingHorizons.pdf")
    print(f"Compiling PDF using WeasyPrint. Output target: {pdf_output_path}...")
    
    try:
        # WeasyPrint will compile from the HTML file, resolving relative paths (like images/maps/...) relative to docs/
        html_doc = HTML(filename=html_output_path)
        html_doc.write_pdf(target=pdf_output_path)
        print("PDF compilation completed successfully!")
        
        # Clean up intermediate HTML file
        if os.path.exists(html_output_path):
            os.remove(html_output_path)
            print("Cleaned up intermediate HTML file.")
            
    except Exception as e:
        print(f"Error compiling PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
