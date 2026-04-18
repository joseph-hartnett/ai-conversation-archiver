# AI Conversation Archiver

Python scripts for converting AI conversation exports into searchable Markdown notes in Obsidian. Currently supports Claude (Anthropic) and ChatGPT (OpenAI).

## Why This Is Different

Browser extensions that capture AI conversations work going forward, one conversation at a time. These scripts do something extensions cannot: they process your entire conversation history in a single pass, including years of past conversations, from the bulk export files that Claude and ChatGPT provide. If you have an existing body of AI-assisted work and want all of it searchable and under your own control, this is the approach.

Full documentation, setup instructions, screenshots, and workflow guidance are available in the [companion LibGuide](https://guides.newman.baruch.cuny.edu/ai-conversation-archiving).

## Background

This project is part of a broader scholarly contribution on cognitive sovereignty: the idea that researchers and learners should maintain meaningful ownership of their AI-assisted intellectual output. AI platforms treat conversation history as a temporary service feature. These scripts treat it as intellectual work product worth keeping. For the conceptual framework, see the companion LibGuide.

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
- Extracted text from uploaded PDFs, Word docs, and text files (matched to filenames using ChatGPT's retrieval index)
- Code blocks with proper formatting

## Requirements

- Python 3.x
- No additional libraries required (uses only Python standard library)
- Obsidian (free): [obsidian.md](https://obsidian.md)

## Setup

**Important:** Both scripts must be placed directly in your `Archive-Scripts/` folder. Do not place them inside subfolders such as `ChatGPT-Export/`. The scripts look for input files in their own directory and will not run correctly from a subfolder.

Full setup instructions with screenshots are in the [companion LibGuide](https://guides.newman.baruch.cuny.edu/ai-conversation-archiving).

## Quick Start

### Claude

1. Export your data from [claude.ai](https://claude.ai) (Settings > Privacy > Export Data)
2. Download and unzip. Move `conversations.json` from Downloads into `Archive-Scripts/` (replace the old one).
3. Run:
```bash
cd ~/Desktop/Archive-Scripts
python3 convert_claude_to_obsidian.py
```
4. Open the generated `Claude-Conversations/` folder as a vault in Obsidian

### ChatGPT

1. Request your export from [chatgpt.com](https://chatgpt.com) (Settings > Data Controls > Export Data). Allow up to 24 hours for the email.
2. Download and unzip. Move `chatgpt_conversations.json` and any PNG files from Downloads into `Archive-Scripts/`.
3. Run:
```bash
cd ~/Desktop/Archive-Scripts
python3 convert_chatgpt_to_obsidian.py
```
4. Open the generated `ChatGPT-Conversations/` folder as a vault in Obsidian

## Output Structure

**Claude Archive**
```
Claude-Conversations/
    00-MASTER-INDEX.md
    Conversations/
    Files/
```

**ChatGPT Archive**
```
ChatGPT-Conversations/
    00-MASTER-INDEX.md
    Conversations/
    Images/
```

## Monthly Workflow

Both scripts are designed to be run monthly after downloading a fresh export. The output folder updates on each run. Keep your source JSON files until the next export as backup. Total time once set up: approximately 5 minutes per platform per month.

## Limitations

**Claude:** Artifact content (scripts, documents created in the artifact panel) is not available in the export and cannot be captured. Artifacts can be retrieved manually from your Claude account. Image files are referenced in the archive but not saved.

**ChatGPT:** Only text extraction from uploaded files is preserved, not the original files. Long documents are truncated at 500 lines or 10,000 characters for readability. The full text remains in the source JSON.

## License

MIT License. Free to use, adapt, and build on. See [LICENSE](LICENSE) for details.
