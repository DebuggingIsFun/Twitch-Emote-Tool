# **Twitch Emote Tool (Python)**
*A cross-platform rewrite of Pewy's Twitch Emote Tool for Linux/Windows/macOS.*

![Python Version](https://img.shields.io/badge/python-3.8+-blue?style=flat-square)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Demo GIF](./assets/Demo_31012026.gif)](./assets/Demo_31012026.gif)

---

## **📌 About This Tool**
Originally created by **[Pewy (Artist)](https://pewy.art/)** and programmed by **Morksen**, this tool allows **bulk creation of Twitch emotes** (up to **40 per export**).

### **Key Features**
- ✅ **Cross-platform** (Linux, Windows, macOS)
- ✅ **Grid-based emote detection** (scans PNG templates for emotes)
- ✅ **Custom naming** (or auto-generated names like `emote1_128x128`)
- ✅ **Transparent background support** (PNG export)
- ✅ **Preview with borders** (green = detected, red = empty)

### **Templates**
- **Old & New templates** are included in `/emote-template`.
- **Must have a transparent background** for proper detection.

<details>
<summary><b>Why This Repo Exists</b> (Click to Expand)</summary>

The original tool was **Windows-only**, but my partner needed it on **Linux**. Since no source code was available, I used my hard-headed nature and got with **trial and error** to this Version.

- **First version**: CLI-only.
- **Current version**: GUI built with **CustomTkinter** (after experimenting with `tkinter`).
- **AI-assisted learning**: Used AI to understand UI components better.

</details>

---

## **🛠️ How It Works**
1. **Input**: Load a **PNG template** (grid-based, with emotes inside cells).
2. **Detection**:
   - Scans **corners/edges** of each grid cell.
   - Blurs and monocroms thems for easiert detection
   - **Green border** = Emote detected.
   - **Red border** = Empty cell (ignored in export).
3. **Naming**:
   - On the Right side you can set **costum names** .
   - If no name is set, uses `emote1_128x128`, `emote2_128x128`, etc.
   - Naming scheme is $name_$plattform_witdh_height.png so like **emote1_twitch_112x112.png**
4. **Export**:
   - Creates a folder `emote_export_multi` in the **same directory as the template**.
   - Example:
     - Template path: `/home/user/art/emote-template.png`
     - Export path: `/home/user/art/emote_export_multi/`
### **Supported Export Platforms**
| Platform | Sizes |
|----------|-------|
| Twitch Emotes | 112, 56, 28 |
| Twitch Badges | 72, 36, 18 |
| Kick | 128, 64, 32 |
| Discord | 128, 64, 32 |
| YouTube | 48, 24 |

---

## **How to Build from soure**
- **Install dependencies** from `requirements.txt`.
- **Run manually**:
  ```bash
  git clone https://github.com/DebuggingIsFun/Twitch-Emote-Tool.git
  cd twitch-emote-tool
  pip install -r requirements.txt
  python main.py

## **💬 A Word of Reason**

This is a **hobby project** I work on in my free time. I'm not a professional developer - just someone who wanted to help my partner use this tool on Linux and learned a lot along the way!

### **What this means:**
- ⏰ Updates may be slow (life happens!)
- 🐛 Bugs are possible - please report them! And make the Debug Checkbox enabled for detailed log! 
- 🎯 Features are added when I have time and motivation

### **What I'd love from you:**
- **Feedback** - What works? What doesn't?
- **Bug reports** - Open an issue on GitHub
- **Ideas** - Suggestions are always welcome
- **Patience** - This is a labor of love, not a job 😄

I truly hope this tool is **useful to artists and streamers** out there. If it saves you even a few minutes of manual resizing, then it was worth building!

---

## **🙏 Credits**
- **[Pewy](https://pewy.art/)** - Original concept & PNG templates
- **Morksen** - Original Windows tool creator
- **DebugginIsFun (kami_no_teki)** - This Python rewrite
- **My Partner**

---