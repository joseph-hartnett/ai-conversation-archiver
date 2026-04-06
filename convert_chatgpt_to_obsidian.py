import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# --- JSON-History backup ---
source = "chatgpt_conversations.json"
history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "JSON-History")
os.makedirs(history_dir, exist_ok=True)

if os.path.exists(source):
    dated_name = f"chatgpt_conversations_{datetime.today().strftime('%Y-%m-%d')}.json"
    dest = os.path.join(history_dir, dated_name)
    if not os.path.exists(dest):
        shutil.copy2(source, dest)
        print(f"Backed up {source} → {dest}")
    else:
        print(f"Backup already exists for today: {dest}")
# --- End backup ---

def sanitize_filename(name, max_length=100):
    """Convert a string to a safe filename"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip()
    if not name:
        name = "Untitled"
    if len(name) > max_length:
        name = name[:max_length].strip()
    return name

def extract_asset_pointer_hash(asset_pointer):
    """Extract file hash from asset pointer"""
    if not asset_pointer:
        return None
    match = re.search(r'file[_-]([0-9a-zA-Z]+)', asset_pointer)
    if match:
        return match.group(1)
    return None

def find_image_file_by_id(file_id, images_dir):
    """Find PNG file by ID"""
    if not file_id:
        return None
    pattern = f"file-{file_id}*.png"
    matches = list(images_dir.glob(pattern))
    if matches:
        return matches[0]
    for png_file in images_dir.glob("*.png"):
        if file_id in png_file.name:
            return png_file
    return None

def find_image_file(file_hash, images_dir):
    """Find PNG file by hash for DALL-E images"""
    if not file_hash:
        return None
    pattern = f"file_{file_hash}*.png"
    matches = list(images_dir.glob(pattern))
    if matches:
        return matches[0]
    return None

def build_message_tree(mapping):
    """Build ordered message list"""
    root_id = None
    for msg_id, msg_data in mapping.items():
        parent = msg_data.get('parent')
        if not parent or parent not in mapping:
            root_id = msg_id
            break
    
    if not root_id:
        root_id = list(mapping.keys())[0]
    
    ordered_messages = []
    
    def traverse(msg_id):
        if msg_id not in mapping:
            return
        msg_data = mapping[msg_id]
        if msg_data and 'message' in msg_data and msg_data['message']:
            ordered_messages.append((msg_id, msg_data))
        children = msg_data.get('children', [])
        for child_id in children:
            traverse(child_id)
    
    traverse(root_id)
    return ordered_messages

def collect_file_info_from_conversation(ordered_messages):
    """
    First pass: collect all file uploads and their extracted content.
    Returns dict mapping file_index -> {file_info, extracted_content}
    """
    files_with_content = {}
    current_files = []
    
    for msg_id, msg_data in ordered_messages:
        message = msg_data.get('message')
        if not message:
            continue
            
        author = message.get('author', {})
        role = author.get('role', 'unknown')
        
        # Check for file uploads in user messages
        if role == 'user':
            metadata = message.get('metadata', {})
            attachments = metadata.get('attachments', [])
            
            if attachments:
                # New file upload - reset current files list
                current_files = []
                for idx, attachment in enumerate(attachments):
                    mime_type = attachment.get('mime_type', '')
                    if not mime_type.startswith('image/'):  # Non-image files
                        file_info = {
                            'index': idx,
                            'id': attachment.get('id', ''),
                            'name': attachment.get('name', 'Unknown'),
                            'mime_type': mime_type,
                            'size': attachment.get('size', 0),
                            'extracted_content': None
                        }
                        current_files.append(file_info)
                        files_with_content[idx] = file_info
        
        # Check for extracted content in tool messages
        elif role == 'tool':
            metadata = message.get('metadata', {})
            file_index = metadata.get('retrieval_file_index')
            
            if file_index is not None and file_index in files_with_content:
                # Get the text content from this tool message
                content = message.get('content', {})
                parts = content.get('parts', [])
                
                text_parts = []
                for part in parts:
                    if isinstance(part, str) and len(part.strip()) > 50:
                        # Skip ChatGPT's instruction messages
                        if 'Make sure to include' not in part and 'Remember you have access' not in part:
                            text_parts.append(part.strip())
                
                if text_parts:
                    # Store the extracted content with this file
                    extracted = '\n\n'.join(text_parts)
                    files_with_content[file_index]['extracted_content'] = extracted
    
    return files_with_content

def format_files_with_content(files_with_content):
    """Format uploaded files with their extracted content"""
    if not files_with_content:
        return ""
    
    formatted = "*📎 Uploaded files & extracted content:*\n\n"
    
    MAX_LINES = 500
    MAX_CHARS = 10000
    
    # Sort by index to maintain order
    for file_index in sorted(files_with_content.keys()):
        file_info = files_with_content[file_index]
        file_type = file_info['mime_type'].split('/')[-1]
        size_kb = file_info['size'] / 1024
        
        formatted += f"**{file_info['name']}** ({file_type}, {size_kb:.1f} KB)\n\n"
        
        if file_info['extracted_content']:
            content = file_info['extracted_content']
            
            # Check if truncation needed
            lines = content.split('\n')
            chars_count = len(content)
            lines_count = len(lines)
            
            truncated = False
            if lines_count > MAX_LINES or chars_count > MAX_CHARS:
                truncated = True
                # Take first MAX_LINES or up to MAX_CHARS
                if lines_count > MAX_LINES:
                    content = '\n'.join(lines[:MAX_LINES])
                if len(content) > MAX_CHARS:
                    content = content[:MAX_CHARS]
                
                # Calculate what was omitted
                remaining_chars = chars_count - len(content)
                remaining_lines = lines_count - len(content.split('\n'))
            
            # Show extracted content
            formatted += f"```\n{content}\n```\n\n"
            
            if truncated:
                formatted += f"*... content truncated ({remaining_chars:,} more characters, ~{remaining_lines} more lines)*\n\n"
        else:
            formatted += "*Content not extracted in export*\n\n"
    
    formatted += "───────────────────────────────────────────────\n\n"
    return formatted

def format_regular_message(message, images_dir, output_images_dir):
    """Format a regular user/assistant message"""
    author = message.get('author', {})
    role = author.get('role', 'unknown')
    create_time = message.get('create_time')
    
    # Parse timestamp
    if create_time:
        try:
            dt = datetime.fromtimestamp(create_time)
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            timestamp = str(create_time)
    else:
        timestamp = "Unknown time"
    
    # Extract text content and DALL-E images
    content = message.get('content', {})
    parts = content.get('parts', [])
    
    text_parts = []
    dalle_images = []
    copied_images = []
    
    for part in parts:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict):
            part_type = part.get('content_type', '')
            if part_type == 'image_asset_pointer':
                metadata_obj = part.get('metadata', {})
                dalle_info = metadata_obj.get('dalle', {})
                
                if dalle_info:  # DALL-E image
                    asset_pointer = part.get('asset_pointer', '')
                    file_hash = extract_asset_pointer_hash(asset_pointer)
                    prompt = dalle_info.get('prompt', '')
                    
                    if file_hash:
                        dalle_images.append({
                            'hash': file_hash,
                            'prompt': prompt
                        })
    
    # Extract uploaded images from metadata
    metadata = message.get('metadata', {})
    attachments = metadata.get('attachments', [])
    uploaded_images = []
    
    for attachment in attachments:
        mime_type = attachment.get('mime_type', '')
        if mime_type.startswith('image/'):
            uploaded_images.append({
                'id': attachment.get('id', ''),
                'name': attachment.get('name', 'Image')
            })
    
    full_text = '\n\n'.join(text_parts)
    
    if not full_text and not dalle_images and not uploaded_images:
        return "", []
    
    # Format output
    formatted = f"**{role.title()} ({timestamp})**\n\n"
    
    # Add uploaded images
    if uploaded_images:
        formatted += "*🖼️ Uploaded images:*\n\n"
        for img in uploaded_images:
            img_file = find_image_file_by_id(img['id'], images_dir)
            if img_file:
                dest_path = output_images_dir / img_file.name
                try:
                    shutil.copy2(img_file, dest_path)
                    copied_images.append(img_file.name)
                    formatted += f"![{img['name']}](../Images/{img_file.name})\n"
                    formatted += f"*Original filename: {img['name']}*\n\n"
                except Exception as e:
                    print(f"  Warning: Could not copy image {img_file.name}: {e}")
        formatted += "\n"
    
    # Add text
    if full_text:
        formatted += full_text + "\n\n"
    
    # Add DALL-E images
    for img in dalle_images:
        img_file = find_image_file(img['hash'], images_dir)
        if img_file:
            dest_path = output_images_dir / img_file.name
            try:
                shutil.copy2(img_file, dest_path)
                copied_images.append(img_file.name)
                formatted += f"![DALL-E Image](../Images/{img_file.name})\n"
                if img['prompt']:
                    formatted += f"*Prompt: {img['prompt']}*\n"
                formatted += "\n"
            except Exception as e:
                print(f"  Warning: Could not copy DALL-E image {img_file.name}: {e}")
    
    formatted += "───────────────────────────────────────────────\n\n"
    return formatted, copied_images

def convert_conversation_to_markdown(conversation, conversations_dir, images_dir, output_images_dir):
    """Convert ChatGPT conversation to markdown with proper file content matching"""
    conv_id = conversation.get('conversation_id', 'unknown')
    title = conversation.get('title', 'Untitled Conversation')
    create_time = conversation.get('create_time', 0)
    update_time = conversation.get('update_time', create_time)
    mapping = conversation.get('mapping', {})
    
    # Parse dates
    try:
        created_dt = datetime.fromtimestamp(create_time)
        updated_dt = datetime.fromtimestamp(update_time if update_time else create_time)
        date_str = created_dt.strftime('%Y-%m-%d')
        date_range = f"{created_dt.strftime('%Y-%m-%d')}"
        if created_dt.date() != updated_dt.date():
            date_range += f" to {updated_dt.strftime('%Y-%m-%d')}"
    except:
        date_str = 'unknown'
        date_range = 'unknown'
    
    # Build message order
    ordered_messages = build_message_tree(mapping)
    if not ordered_messages:
        return None
    
    # FIRST PASS: Collect file uploads and their extracted content
    files_with_content = collect_file_info_from_conversation(ordered_messages)
    
    # Create safe filename
    safe_title = sanitize_filename(title, max_length=80)
    filename = f"{date_str}_{safe_title}.md"
    filepath = conversations_dir / filename
    
    # Build markdown content
    content = f"""═══════════════════════════════════════════════
# {title} ({date_range})
═══════════════════════════════════════════════

{len(ordered_messages)} messages

## Conversation

"""
    
    # Track all images
    all_images = []
    files_displayed = False
    
    # SECOND PASS: Format messages for display
    for msg_id, msg_data in ordered_messages:
        try:
            message = msg_data.get('message')
            if not message:
                continue
            
            author = message.get('author', {})
            role = author.get('role', 'unknown')
            
            # Skip system and tool messages (tool content already collected)
            if role in ['system', 'tool']:
                continue
            
            # If this is a user message with file uploads, display files first
            metadata = message.get('metadata', {})
            attachments = metadata.get('attachments', [])
            has_non_image_files = any(not att.get('mime_type', '').startswith('image/') 
                                     for att in attachments)
            
            if has_non_image_files and not files_displayed:
                # Display collected files with their content
                content += format_files_with_content(files_with_content)
                files_displayed = True
            
            # Format regular message
            msg_content, msg_images = format_regular_message(message, images_dir, output_images_dir)
            content += msg_content
            all_images.extend(msg_images)
            
        except Exception as e:
            print(f"  Warning: Error processing message in {title}: {e}")
            continue
    
    # Add images summary
    if all_images:
        content += "\n\n───────────────────────────────────────────────\n\n"
        content += "## Images in This Conversation\n\n"
        for img in all_images:
            content += f"- [[{img}]]\n"
    
    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return {
        'filename': filename,
        'title': title,
        'conversation_id': conv_id,
        'created': datetime.fromtimestamp(create_time).isoformat() if create_time else 'unknown',
        'updated': datetime.fromtimestamp(update_time).isoformat() if update_time else 'unknown',
        'date_range': date_range,
        'message_count': len(ordered_messages),
        'image_count': len(all_images),
        'images': all_images
    }

def create_master_index(conversation_metadata, output_file):
    """Create master index"""
    sorted_convos = sorted(conversation_metadata, key=lambda x: x['created'], reverse=True)
    total_images = sum(c['image_count'] for c in conversation_metadata)
    
    content = f"""# ChatGPT Conversation Master Index

**Total Conversations:** {len(conversation_metadata)}  
**Total Images:** {total_images}  
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## What This Archive Contains

**✅ Captured:**
- All conversation text
- DALL-E generated images with prompts
- Images you uploaded  
- Uploaded file names AND extracted text content
- Code blocks and examples

**❌ Not Captured:**
- Voice conversations
- Binary file content (only text extraction)

---

## Conversations

"""
    
    current_month = None
    for convo in sorted_convos:
        try:
            convo_date = datetime.fromisoformat(convo['created'])
            month_str = convo_date.strftime('%B %Y')
            if month_str != current_month:
                content += f"\n### {month_str}\n\n"
                current_month = month_str
        except:
            pass
        
        content += f"**{convo['date_range']}** - [[{convo['filename']}|{convo['title']}]]"
        if convo['image_count'] > 0:
            content += f" `({convo['image_count']} images)`"
        content += "\n"
        
        if convo['images']:
            for img in convo['images']:
                content += f"  - 🖼️ [[{img}]]\n"
        content += "\n"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """Main conversion"""
    print("="*60)
    print("CHATGPT CONVERSATIONS TO OBSIDIAN CONVERTER v3")
    print("Now with matched file content extraction!")
    print("="*60)
    print()
    
    input_file = Path("chatgpt_conversations.json")
    images_source = Path(".")
    output_base = Path("Archive-ChatGPT")
    
    if not input_file.exists():
        print("❌ ERROR: chatgpt_conversations.json not found!")
        return
    
    conversations_dir = output_base / "Conversations"
    images_dir = output_base / "Images"
    
    print(f"Creating directory structure...")
    output_base.mkdir(exist_ok=True)
    conversations_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)
    
    print(f"Loading {input_file.name}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
    except Exception as e:
        print(f"❌ ERROR: Could not read JSON file: {e}")
        return
    
    print(f"Found {len(conversations)} conversations")
    print()
    
    print("Converting conversations...")
    metadata = []
    
    for i, conv in enumerate(conversations):
        try:
            conv_meta = convert_conversation_to_markdown(
                conv, conversations_dir, images_source, images_dir
            )
            
            if conv_meta:
                metadata.append(conv_meta)
            
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(conversations)} conversations...")
        except Exception as e:
            print(f"  ⚠️  Error processing conversation {i}: {e}")
            continue
    
    print(f"  ✅ Completed: {len(metadata)} conversations converted")
    print()
    
    print("Creating master index...")
    index_file = output_base / "00-MASTER-INDEX.md"
    create_master_index(metadata, index_file)
    
    total_images = sum(c['image_count'] for c in metadata)
    
    print()
    print("="*60)
    print("✨ CONVERSION COMPLETE! ✨")
    print("="*60)
    print(f"📁 Output location: {output_base.absolute()}")
    print(f"💬 {len(metadata)} conversations → {conversations_dir.name}/")
    print(f"🖼️  {total_images} images → {images_dir.name}/")
    print(f"📋 Master index → {index_file.name}")
    print()
    print("🎉 Your ChatGPT archive with extracted file content is ready!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Conversion cancelled")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
