# AI Conversation Archiver

Python scripts for converting AI conversation exports into searchable 
Markdown notes in Obsidian.

Currently supports Claude (Anthropic) and ChatGPT (OpenAI).

## Why This Exists

AI platforms don't make it easy to search, reference, or build on past 
conversations. These scripts take the data export files that Claude and 
ChatGPT provide, convert them into plain Markdown files, and organize them 
into an Obsidian vault — giving you a fully searchable, portable archive 
of your AI-assisted intellectual work that you own and control.

## What Gets Captured

**Claude**
- Full conversation text
- Uploaded text files (saved as .md for Obsidian searchability)
- Web search queries and results
- Tool usage (bash commands, file operations, conversation searches)
- Code blocks with proper formatting

**ChatGPT**
- Full conversation text
- DALL-E generated images and user-uploaded images
- Extracted text from uploaded PDFs, Word docs, and text files
  (matched to specific filenames using ChatGPT's retrieval index)
- Code blocks with proper formatting

## Requirements

- Python 3
- No additional libraries required (uses only Python standard library)
- Obsidian (free) — [obsidian.md](https://obsidian.md)

## Quick Start

### Claude

1. Export your data from [claude.ai](https://claude.ai) (Settings → Export)
2. Extract the zip and locate `conversations.json`
3. Place `conversations.json` in the same folder as the script
4. Run:
```bash
python3 claude/convert_to_obsidian.py
```

5. Open the generated `Archive/` folder as a vault in Obsidian

### ChatGPT

1. Export your data from [chatgpt.com](https://chatgpt.com) 
   (Settings → Data controls → Export data)
2. Wait for the email with your download link
3. Unzip the export and place these files in a working folder:
   - Rename `conversations.json` → `chatgpt_conversations.json`
   - Copy all `.png` image files to the same folder
4. Run:
```bash
python3 chatgpt/convert_chatgpt_to_obsidian.py
```

5. Move the generated `Archive-ChatGPT/` folder to your preferred location
6. Open in Obsidian

## Script Variants (Claude)

Two versions are included:

| Script | Description |
|--------|-------------|
| `convert_to_obsidian.py` | Standard version. Preserves original file types for uploaded files. |
| `convert_to_obsidian_txt_as_md.py` | Saves all uploaded text files as `.md` for better Obsidian searchability. |

The `.md` variant is recommended if searchability is your priority.

## Output Structure

**Claude Archive**
```
Archive/
├── 00-MASTER-INDEX.md
├── Conversations/
└── Files/
```

**ChatGPT Archive**
```
Archive-ChatGPT/
├── 00-MASTER-INDEX.md
├── Conversations/
└── Images/
```

## Limitations

**Claude:** Artifact content (scripts, documents created in `<artifact>` 
tags) is not available in the export and cannot be captured. Image files 
are referenced but not saved. Project-uploaded files are not included in exports and must be managed manually.

**ChatGPT:** Only text extraction from uploaded files is available (not 
the original binary files). Long documents are truncated at 500 lines or 
10,000 characters for readability — the full text is in the source JSON.

## Monthly Workflow

Both scripts are designed to be run monthly after downloading a fresh 
export. The output folder is overwritten each run. Keep your source 
JSON files until the next export as backup.

## Background

These scripts were developed as part of a broader project on cognitive 
sovereignty — the idea that researchers and learners should maintain 
meaningful ownership of their AI-assisted intellectual work. 

For more on the conceptual framework, see the related LibGuide: [link TBD]

## License

MIT License — see [LICENSE](LICENSE) for details.
