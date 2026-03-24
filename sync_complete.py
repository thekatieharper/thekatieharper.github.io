#!/usr/bin/env python3
"""
Complete Website Sync from Notion
- Generates HTML for writing posts
- Auto-updates homepage Writing section
- Handles external links with UTM tracking

Usage:
python3 sync_complete.py
"""

import os
import requests
import markdown2
import re

# Configuration
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
DATABASE_ID = '31fe8f3225f780e6a580d7405b9c152d'
NOTION_VERSION = '2022-06-28'

HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Content-Type': 'application/json',
    'Notion-Version': NOTION_VERSION
}

def fetch_published_items():
    """Fetch all published items from Notion"""
    url = f'https://api.notion.com/v1/databases/{DATABASE_ID}/query'
    
    data = {
        "filter": {
            "property": "Status",
            "select": {
                "equals": "Published"
            }
        }
    }
    
    response = requests.post(url, headers=HEADERS, json=data)
    
    if response.status_code != 200:
        print(f"Error fetching items: {response.text}")
        return []
    
    results = response.json()
    
    items = []
    for page in results['results']:
        props = page['properties']
        
        # Extract properties with safe defaults
        title_array = props.get('Title', {}).get('title', [])
        title = title_array[0].get('plain_text', '') if title_array else ''
        
        desc_array = props.get('Description', {}).get('rich_text', [])
        description = desc_array[0].get('plain_text', '') if desc_array else ''
        
        slug_array = props.get('Slug', {}).get('rich_text', [])
        slug = slug_array[0].get('plain_text', '') if slug_array else ''
        
        category = props.get('Category', {}).get('select', {}).get('name', 'Tactical')
        item_type = props.get('Type', {}).get('select', {}).get('name', 'Post')
        url = props.get('URL', {}).get('url', '')
        
        if title:
            items.append({
                'id': page['id'],
                'title': title,
                'description': description,
                'slug': slug,
                'category': category,
                'type': item_type,
                'url': url
            })
    
    return items

def fetch_page_content(page_id):
    """Fetch the content blocks from a Notion page"""
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Error fetching content: {response.text}")
        return ""
    
    blocks = response.json()
    content_parts = []
    prev_was_list = False
    
    for block in blocks['results']:
        block_type = block['type']
        
        if block_type == 'heading_1':
            if prev_was_list:
                content_parts.append('\n')  # Extra space after lists
            text = ''.join([t['plain_text'] for t in block['heading_1']['rich_text']])
            content_parts.append(f"\n# {text}\n\n")
            prev_was_list = False
        
        elif block_type == 'heading_2':
            if prev_was_list:
                content_parts.append('\n')
            text = ''.join([t['plain_text'] for t in block['heading_2']['rich_text']])
            content_parts.append(f"\n## {text}\n\n")
            prev_was_list = False
        
        elif block_type == 'heading_3':
            if prev_was_list:
                content_parts.append('\n')
            text = ''.join([t['plain_text'] for t in block['heading_3']['rich_text']])
            content_parts.append(f"\n### {text}\n\n")
            prev_was_list = False
        
        elif block_type == 'paragraph':
            if prev_was_list:
                content_parts.append('\n')  # Extra space after lists
            rich_text = block['paragraph']['rich_text']
            text = ''
            for t in rich_text:
                content = t['plain_text']
                annotations = t.get('annotations', {})
                
                # Apply formatting
                if annotations.get('bold'):
                    content = f"**{content}**"
                if annotations.get('italic'):
                    content = f"*{content}*"
                if annotations.get('code'):
                    content = f"`{content}`"
                if t.get('href'):
                    content = f"[{content}]({t['href']})"
                    
                text += content
            if text.strip():
                content_parts.append(f"{text}\n\n")
            prev_was_list = False
        
        elif block_type == 'bulleted_list_item':
            rich_text = block['bulleted_list_item']['rich_text']
            text = ''
            for t in rich_text:
                content = t['plain_text']
                annotations = t.get('annotations', {})
                
                if annotations.get('bold'):
                    content = f"**{content}**"
                if annotations.get('italic'):
                    content = f"*{content}*"
                if t.get('href'):
                    content = f"[{content}]({t['href']})"
                    
                text += content
            content_parts.append(f"* {text}\n")
            prev_was_list = True
        
        elif block_type == 'numbered_list_item':
            rich_text = block['numbered_list_item']['rich_text']
            text = ''
            for t in rich_text:
                content = t['plain_text']
                annotations = t.get('annotations', {})
                
                if annotations.get('bold'):
                    content = f"**{content}**"
                if annotations.get('italic'):
                    content = f"*{content}*"
                if t.get('href'):
                    content = f"[{content}]({t['href']})"
                    
                text += content
            content_parts.append(f"1. {text}\n")
            prev_was_list = True
        
        elif block_type == 'quote':
            if prev_was_list:
                content_parts.append('\n')
            text = ''.join([t['plain_text'] for t in block['quote']['rich_text']])
            content_parts.append(f"\n> {text}\n\n")
            prev_was_list = False
        
        elif block_type == 'divider':
            if prev_was_list:
                content_parts.append('\n')
            content_parts.append('\n---\n\n')
            prev_was_list = False
    
    return ''.join(content_parts)

def generate_post_html(item, markdown_content):
    """Generate HTML file for a blog post"""
    
    # Convert markdown to HTML
    html_content = markdown2.markdown(markdown_content, extras=['fenced-code-blocks', 'tables'])
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{item['title']}</title>
    <meta name="description" content="{item['description']}">
    <meta name="author" content="Katie Harper">
    
    <!-- Open Graph / Social Media -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://thekatieharper.com/{item['slug']}.html">
    <meta property="og:title" content="{item['title']}">
    <meta property="og:description" content="{item['description']}">
    <meta property="og:image" content="https://thekatieharper.com/social-share.png">
    
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:site" content="@thekatieharper">
    <meta name="twitter:creator" content="@thekatieharper">
    <meta name="twitter:image" content="https://thekatieharper.com/social-share.png">
    
    <link rel="icon" type="image/png" href="favicon.png">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <p><a href="index.html">← Home</a></p>
        
        {html_content}
    </div>
</body>
</html>
"""
    return html

def add_utm_to_url(url):
    """Add UTM tracking to external URLs"""
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}ref=katieharper"

def generate_writing_section(items):
    """Generate the Writing section HTML for homepage"""
    
    # Group items by category
    tactical = [item for item in items if item['category'] == 'Tactical']
    personal = [item for item in items if item['category'] == 'Personal']
    recs = [item for item in items if item['category'] == 'Recommendations']
    
    html = '<h2>Writing</h2>\n\n'
    
    # Tactical startup advice
    if tactical:
        html += '<p>Tactical startup advice:</p>\n\n<p>'
        links = []
        for item in tactical:
            if item['type'] == 'Post':
                links.append(f'<a href="{item["slug"]}.html">{item["title"]}</a>')
            else:
                tracked_url = add_utm_to_url(item['url'])
                links.append(f'<a href="{tracked_url}">{item["title"]}</a>')
        html += ' · '.join(links)
        html += '</p>\n\n'
    
    # Other life thoughts
    if personal:
        html += '<p>Other life thoughts:</p>\n\n<p>'
        links = []
        for item in personal:
            if item['type'] == 'Post':
                links.append(f'<a href="{item["slug"]}.html">{item["title"]}</a>')
            else:
                tracked_url = add_utm_to_url(item['url'])
                links.append(f'<a href="{tracked_url}">{item["title"]}</a>')
        html += ' · '.join(links)
        html += '</p>\n\n'
    
    # Recommendations
    if recs:
        html += '<p>Recommendations:</p>\n\n<p>'
        links = []
        for item in recs:
            tracked_url = add_utm_to_url(item['url'])
            links.append(f'<a href="{tracked_url}">{item["title"]}</a>')
        html += ' · '.join(links)
        html += '</p>\n\n'
    
    return html

def update_homepage(writing_html):
    """Update index.html with new Writing section"""
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("⚠️  index.html not found - make sure you're in the right directory")
        return False
    
    # Replace everything between <h2>Writing</h2> and the next <hr>
    # The writing_html already includes <h2>Writing</h2> so we replace it entirely
    pattern = r'<h2>Writing</h2>.*?<hr>'
    replacement = f'{writing_html}<hr>'
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content == content:
        print("⚠️  Could not find Writing section in index.html")
        return False
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    """Main sync function"""
    print("🔄 Syncing from Notion...\n")
    
    # Fetch all published items
    print("📥 Fetching published items...")
    items = fetch_published_items()
    
    if not items:
        print("⚠️  No published items found")
        return
    
    print(f"   Found {len(items)} items\n")
    
    # Generate HTML for posts (not links)
    posts = [item for item in items if item['type'] == 'Post']
    print(f"📝 Generating {len(posts)} post pages...")
    
    for item in posts:
        print(f"   Processing: {item['title']}")
        
        # Fetch page content
        content = fetch_page_content(item['id'])
        
        # Generate HTML
        html = generate_post_html(item, content)
        
        # Write to file
        filename = f"{item['slug']}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"     ✓ Generated {filename}")
    
    # Update homepage Writing section
    print(f"\n🏠 Updating homepage Writing section...")
    writing_html = generate_writing_section(items)
    
    if update_homepage(writing_html):
        print("   ✓ Updated index.html")
    else:
        print("   ✗ Failed to update index.html")
    
    print(f"\n✅ Sync complete!")
    print(f"\nNext steps:")
    print(f"  git add *.html")
    print(f"  git commit -m \"Update writing from Notion\"")
    print(f"  git push")

if __name__ == '__main__':
    main()
