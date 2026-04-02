import json
import os
import re
from datetime import datetime
from pathlib import Path

# CONFIGURATION
INCLUDE_THINKING = False  # Set to True to include Claude's internal reasoning blocks

def sanitize_filename(name, max_length=100):
    """Convert a string to a safe filename"""
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip()
    if not name:
        name = "Untitled"
    # Limit length
    if len(name) > max_length:
        name = name[:max_length].strip()
    return name

def format_code_block(language, code):
    """Format a code block in markdown"""
    return f"```{language}\n{code}\n```\n"

def format_tool_use(tool_data):
    """Format tool use for display"""
    tool_name = tool_data.get('name', 'unknown')
    tool_input = tool_data.get('input', {})
    description = tool_data.get('description', '')
    message = tool_data.get('message', '')
    
    output = f"**🔧 Tool Used: {tool_name}**\n"
    
    if message:
        output += f"*{message}*\n"
    
    if description:
        output += f"*{description}*\n"
    
    # Format specific tool inputs
    if tool_name == 'web_search' and 'query' in tool_input:
        output += f"Search query: `{tool_input['query']}`\n"
    elif tool_name == 'bash_tool' and 'command' in tool_input:
        output += f"Command: `{tool_input['command']}`\n"
    elif tool_name == 'conversation_search' and 'query' in tool_input:
        output += f"Search query: `{tool_input['query']}`\n"
    
    return output + "\n"

def format_tool_result(tool_data):
    """Format tool results for display"""
    tool_name = tool_data.get('name', 'unknown')
    content = tool_data.get('content', [])
    is_error = tool_data.get('is_error', False)
    error_msg = tool_data.get('message', '')
    
    output = ""
    
    if is_error:
        output += f"**❌ Tool Error: {tool_name}**\n"
        if error_msg:
            output += f"Error: {error_msg}\n"
        return output + "\n"
    
    if tool_name == 'web_search':
        output += "**🔍 Search Results:**\n\n"
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'knowledge':
                title = item.get('title', 'Untitled')
                url = item.get('url', '')
                text_snippet = item.get('text', '')
                
                output += f"**[{title}]({url})**\n"
                if text_snippet:
                    # Truncate long snippets
                    if len(text_snippet) > 300:
                        text_snippet = text_snippet[:300] + "..."
                    output += f"> {text_snippet}\n\n"
    
    elif tool_name == 'artifacts':
        output += "**📦 Artifact Created**\n"
        output += "*Note: Artifact content is not included in Claude exports. Download artifacts during the conversation to save them.*\n\n"
    
    elif tool_name == 'present_files':
        output += "**📄 Files Created by Claude:**\n"
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'local_resource':
                file_name = item.get('name', 'Unknown file')
                file_path = item.get('file_path', '')
                output += f"- {file_name}\n"
                output += f"  *Path: `{file_path}`*\n"
                output += "  *Note: File content not included in export*\n"
        output += "\n"
    
    elif tool_name == 'bash_tool':
        output += "**💻 Command Result:**\n"
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                result_text = item.get('text', '')
                if result_text:
                    output += f"```\n{result_text}\n```\n"
    
    return output

def process_content_items(content_items):
    """Process content array and return formatted text and metadata"""
    text_parts = []
    code_blocks = []
    tool_uses = []
    tool_results = []
    thinking_blocks = []
    
    for item in content_items:
        if not isinstance(item, dict):
            continue
        
        item_type = item.get('type', '')
        
        if item_type == 'text':
            text_parts.append(item.get('text', ''))
        
        elif item_type == 'code_block':
            language = item.get('language', 'text')
            code = item.get('code', '')
            code_blocks.append(format_code_block(language, code))
        
        elif item_type == 'tool_use':
            tool_uses.append(format_tool_use(item))
        
        elif item_type == 'tool_result':
            tool_results.append(format_tool_result(item))
        
        elif item_type == 'thinking' and INCLUDE_THINKING:
            thinking_text = item.get('thinking', '')
            if thinking_text:
                thinking_blocks.append(f"**[Claude's Internal Thinking]**\n> {thinking_text}\n\n")
    
    return {
        'text': '\n\n'.join(text_parts),
        'code_blocks': code_blocks,
        'tool_uses': tool_uses,
        'tool_results': tool_results,
        'thinking': thinking_blocks
    }

def save_uploaded_file(attachment, files_dir, conversation_uuid):
    """Save an uploaded file to the Files directory"""
    file_name = attachment.get('file_name', 'unnamed_file')
    file_type = attachment.get('file_type', 'txt')
    extracted_content = attachment.get('extracted_content', '')
    file_size = attachment.get('file_size', 0)
    
    # Skip if no content
    if not extracted_content:
        return None
    
    # Create safe filename
    if not file_name or file_name.strip() == '':
        file_name = f"uploaded_file_{conversation_uuid[:8]}"
    
    safe_name = sanitize_filename(file_name)
    
    # Clean up file_type - handle cases like "text/plain" 
    if '/' in file_type:
        file_type = file_type.split('/')[-1]  # Get "plain" from "text/plain"
    if file_type == 'plain':
        file_type = 'txt'  # Convert "plain" to "txt"
    
    # SPECIAL: Convert text files to .md for Obsidian searchability
    if file_type == 'txt':
        file_type = 'md'
    
    # Add extension if not present
    if not safe_name.endswith(f".{file_type}"):
        safe_name = f"{safe_name}.{file_type}"
    
    file_path = files_dir / safe_name
    
    # Handle duplicate filenames
    counter = 1
    original_path = file_path
    while file_path.exists():
        stem = original_path.stem
        suffix = original_path.suffix
        file_path = files_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    # Save the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(extracted_content)
    
    return {
        'filename': file_path.name,
        'original_name': file_name,
        'size': file_size,
        'type': file_type
    }

def format_message(message, files_dir, conversation_uuid):
    """Format a single message with proper markdown"""
    sender = message.get('sender', 'unknown')
    created = message.get('created_at', '')
    text = message.get('text', '')
    content = message.get('content', [])
    attachments = message.get('attachments', [])
    files = message.get('files', [])
    
    # Parse timestamp
    try:
        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        timestamp = created_dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        timestamp = created
    
    # Process attachments (uploaded files)
    uploaded_files = []
    for attachment in attachments:
        saved_file = save_uploaded_file(attachment, files_dir, conversation_uuid)
        if saved_file:
            uploaded_files.append(saved_file)
    
    # Process image/file references (these don't have content)
    file_references = []
    for file_ref in files:
        file_name = file_ref.get('file_name', 'unknown')
        if file_name:
            file_references.append(file_name)
    
    # Process content items
    processed = process_content_items(content)
    
    # Build formatted message
    formatted = f"### {sender.title()} ({timestamp})\n\n"
    
    # Add thinking blocks if enabled
    if processed['thinking']:
        formatted += ''.join(processed['thinking'])
    
    # Add uploaded files section
    if uploaded_files:
        formatted += "**📎 Uploaded Files:**\n"
        for uf in uploaded_files:
            formatted += f"- [[{uf['filename']}|{uf['original_name']}]] ({uf['type']}, {uf['size']} bytes)\n"
        formatted += "\n"
    
    # Add file references (images, etc. without content)
    if file_references:
        formatted += "**🖼️ Files Referenced (content not in export):**\n"
        for fr in file_references:
            formatted += f"- {fr}\n"
        formatted += "\n"
    
    # Add tool uses
    if processed['tool_uses']:
        formatted += ''.join(processed['tool_uses'])
    
    # Add main text content
    if processed['text']:
        formatted += processed['text'] + "\n\n"
    
    # Add code blocks
    if processed['code_blocks']:
        formatted += ''.join(processed['code_blocks']) + "\n"
    
    # Add tool results
    if processed['tool_results']:
        formatted += ''.join(processed['tool_results'])
    
    formatted += "\n"
    
    return formatted, uploaded_files

def convert_conversation_to_markdown(conversation, conversations_dir, files_dir):
    """Convert a single conversation to markdown file"""
    uuid = conversation.get('uuid', 'unknown')
    name = conversation.get('name', 'Untitled Conversation')
    created = conversation.get('created_at', '')
    updated = conversation.get('updated_at', '')
    messages = conversation.get('chat_messages', [])
    
    # Parse dates
    try:
        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
        date_str = created_dt.strftime('%Y-%m-%d')
        date_range = f"{created_dt.strftime('%Y-%m-%d')}"
        if created_dt.date() != updated_dt.date():
            date_range += f" to {updated_dt.strftime('%Y-%m-%d')}"
    except:
        date_str = created[:10] if created else 'unknown'
        date_range = date_str
    
    # Create safe filename
    safe_name = sanitize_filename(name, max_length=80)
    filename = f"{date_str}_{safe_name}.md"
    filepath = conversations_dir / filename
    
    # Build markdown content
    content = f"""---
uuid: {uuid}
title: {name}
created: {created}
updated: {updated}
date_range: {date_range}
message_count: {len(messages)}
---

# {name}

**Date Range:** {date_range}  
**Messages:** {len(messages)}  
**UUID:** {uuid}

---

## Conversation

"""
    
    # Track all uploaded files in this conversation
    all_uploaded_files = []
    
    # Add all messages
    for msg in messages:
        try:
            msg_content, msg_files = format_message(msg, files_dir, uuid)
            content += msg_content
            all_uploaded_files.extend(msg_files)
        except Exception as e:
            print(f"  Warning: Error processing message in {name}: {e}")
            continue
    
    # Add uploaded files summary at end
    if all_uploaded_files:
        content += "\n\n---\n\n## Uploaded Files in This Conversation\n\n"
        for uf in all_uploaded_files:
            content += f"- [[{uf['filename']}|{uf['original_name']}]]\n"
    
    # Write conversation file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return {
        'filename': filename,
        'name': name,
        'uuid': uuid,
        'created': created,
        'updated': updated,
        'date_range': date_range,
        'message_count': len(messages),
        'uploaded_files_count': len(all_uploaded_files),
        'uploaded_files': [uf['filename'] for uf in all_uploaded_files]
    }

def create_master_index(conversation_metadata, output_file):
    """Create the master chronological index"""
    
    # Sort by creation date
    sorted_convos = sorted(conversation_metadata, 
                          key=lambda x: x['created'], 
                          reverse=True)  # Most recent first
    
    total_uploaded_files = sum(c['uploaded_files_count'] for c in conversation_metadata)
    
    content = f"""# Claude Conversation Master Index

**Total Conversations:** {len(conversation_metadata)}  
**Total Uploaded Files Recovered:** {total_uploaded_files}  
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This index contains all your Claude conversations with links, dates, and uploaded files.

---

## How to Use This Index

- **Search:** Use Ctrl/Cmd + F to search for keywords
- **Click links:** Click any conversation link to open it
- **By date:** Conversations are listed chronologically (most recent first)
- **Files:** See what files you uploaded in each conversation

---

## What This Archive Contains

**✅ Captured:**
- All conversation text
- Uploaded text files (PDFs, documents, etc.)
- Web search queries and results
- Tool usage (bash commands, file operations)
- Code blocks and examples
- Tool errors and debugging info

**❌ Not Captured (limitations of Claude export):**
- Artifact content (scripts, guides Claude created as artifacts)
- Images you uploaded (references only)
- Content of files Claude created with present_files tool

**💡 Tip:** When Claude creates important artifacts or files during a conversation, download them immediately to save separately.

---

## Conversations

"""
    
    current_month = None
    for convo in sorted_convos:
        # Add month headers
        try:
            convo_date = datetime.fromisoformat(convo['created'].replace('Z', '+00:00'))
            month_str = convo_date.strftime('%B %Y')
            if month_str != current_month:
                content += f"\n### {month_str}\n\n"
                current_month = month_str
        except:
            pass
        
        # Add conversation entry
        content += f"**{convo['date_range']}** - [[{convo['filename']}|{convo['name']}]]"
        
        if convo['uploaded_files_count'] > 0:
            content += f" `({convo['uploaded_files_count']} files)`"
        
        content += "\n"
        
        # Add file list if any
        if convo['uploaded_files']:
            for file in convo['uploaded_files']:
                content += f"  - 📄 [[{file}]]\n"
        
        content += "\n"
    
    # Write index
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """Main conversion function"""
    print("="*60)
    print("CLAUDE CONVERSATIONS TO OBSIDIAN CONVERTER v2")
    print("PERSONAL VERSION: Text files saved as .md for searchability")
    print("="*60)
    print()
    
    # File paths
    input_file = "conversations.json"
    output_base = Path("Archive")
    
    # Create directory structure
    conversations_dir = output_base / "Conversations"
    files_dir = output_base / "Files"
    
    print(f"Creating directory structure...")
    output_base.mkdir(exist_ok=True)
    conversations_dir.mkdir(exist_ok=True)
    files_dir.mkdir(exist_ok=True)
    
    # Load JSON
    print(f"Loading {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
    except FileNotFoundError:
        print(f"\n❌ ERROR: {input_file} not found!")
        print("Make sure conversations.json is in the same folder as this script.")
        return
    except json.JSONDecodeError as e:
        print(f"\n❌ ERROR: Invalid JSON in {input_file}")
        print(f"Details: {e}")
        return
    
    print(f"Found {len(conversations)} conversations")
    print()
    
    # Convert each conversation
    print("Converting conversations...")
    metadata = []
    
    for i, convo in enumerate(conversations):
        try:
            convo_meta = convert_conversation_to_markdown(
                convo, 
                conversations_dir, 
                files_dir
            )
            metadata.append(convo_meta)
            
            # Progress update
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(conversations)} conversations...")
        except Exception as e:
            print(f"  ⚠️  Error processing conversation {i}: {e}")
            continue
    
    print(f"  ✅ Completed: {len(metadata)} conversations converted")
    print()
    
    # Create master index
    print("Creating master index...")
    index_file = output_base / "00-MASTER-INDEX.md"
    create_master_index(metadata, index_file)
    
    # Summary
    total_files = sum(c['uploaded_files_count'] for c in metadata)
    
    print()
    print("="*60)
    print("✨ CONVERSION COMPLETE! ✨")
    print("="*60)
    print(f"📁 Output location: {output_base.absolute()}")
    print(f"💬 {len(metadata)} conversations → {conversations_dir.name}/")
    print(f"📄 {total_files} uploaded files → {files_dir.name}/")
    print(f"📋 Master index → {index_file.name}")
    print()
    print("Next steps:")
    print("1. Open Obsidian")
    print("2. File → Open Vault → Open folder as vault")
    print(f"3. Navigate to: {output_base.absolute()}")
    print("4. Start with 00-MASTER-INDEX.md")
    print()
    print("🎉 Your enhanced archive is ready!")
    print()
    print("Note: This version captures uploaded files, web searches,")
    print("tool usage, and much more than the previous version!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Conversion cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
