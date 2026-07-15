# OpenWebUI Gemini Omni Video Generator

![OpenWebUI Gemini Omni Video Generator Demo](https://github.com/spawnofsociety2/openwebui-gemini-omni-video/raw/master/assets/OpenWebUI_VideoGEN.jpg)

Generate hyper-realistic videos directly within [OpenWebUI](https://openwebui.com/) using Google's **Gemini Omni Flash Preview** model!

This tool takes your prompt, calls the API to generate a high-quality video, downloads it directly to OpenWebUI's static cache, and embeds a gorgeous, fully responsive native HTML5 video player right into your chat stream.

> **Note:** This tool runs on Google's **Gemini Enterprise Agent Platform** (formerly Vertex AI). The 2026 rebrand changed the Cloud Console product name and some IAM role labels, but the API endpoint (`aiplatform.googleapis.com`), model IDs, and SDKs are unchanged — so the setup below works as-is.

## Features

✨ **Native Chat Embeds**: Uses `HTMLResponse` to display the video directly inline so you don't have to leave the chat.  
✨ **Image-to-Video**: Upload reference images directly in the OpenWebUI chat, or paste image URLs, and Omni Flash will use them to generate videos!  
✨ **Video Editing**: Edit existing videos! Upload a video or provide a Google Cloud Storage (`gs://`) link, and ask Omni to edit the video with a prompt.  
📏 **Dynamic Resizing**: Built-in `postMessage` Javascript script seamlessly communicates with the OpenWebUI iframe sandboxing to ensure the player resizes perfectly to a 16:9 aspect ratio without ugly scrollbars or getting cut off.  
☁️ **Platform Ready**: Uses Application Default Credentials (ADC) to securely connect to your Google Cloud Project.  
📦 **Zero-Touch Installation**: The required `google-genai`, `google-auth`, and `google-cloud-storage` SDKs are automatically installed by OpenWebUI upon importing the tool.

## Prerequisites & Authentication

You must have a Google Cloud Project with the **Gemini Enterprise Agent Platform (formerly Vertex AI) API** enabled. Unlike OpenAI, Google requires proper IAM Authentication rather than a simple API key. Here is how to set it up depending on how you installed OpenWebUI:

### Option 1: You installed via Python (`pip` / `uv`)

1. Install the Google Cloud SDK (`gcloud` CLI) on your host machine.
2. Open your terminal/command prompt and run: `gcloud auth application-default login`
3. A browser window will open. Log into your Google Cloud account.
4. Restart your OpenWebUI Python server. The script will automatically detect the credentials!

### Option 2: You installed via Docker

Since OpenWebUI runs inside an isolated container, that container needs to be handed your Google Cloud credentials.

1. Go to your Google Cloud Console and navigate to **IAM & Admin > Service Accounts**.
2. Create a new Service Account and grant it the `Vertex AI User` role. *(The console may show this under a renamed label after the 2026 rebrand — the underlying permission is the same.)*
3. Click on the Service Account, go to the **Keys** tab, and select **Add Key > Create New Key > JSON**. This will download a `.json` file.
4. Move this JSON file into your OpenWebUI data directory on your host (for example, name it `gcp-key.json`).
5. Update your OpenWebUI `docker run` command (or `docker-compose.yml`) to add this environment variable:
`-e GOOGLE_APPLICATION_CREDENTIALS="/app/backend/data/gcp-key.json"` *(Note: Adjust the container path based on where your OpenWebUI data volume is mounted).*

### Option 3: You installed via Kubernetes (Helm)

1. Download your Service Account JSON key from Google Cloud (same as Docker steps 1-3).
2. Create a secret in your OpenWebUI namespace:
`kubectl create secret generic vertex-auth --from-file=gcp-key.json=./gcp-key.json`
3. Update your OpenWebUI Helm `values.yaml` to mount this secret:

```yaml
extraEnvVars:
  - name: GOOGLE_APPLICATION_CREDENTIALS
    value: "/auth/gcp-key.json"
extraVolumes:
  - name: vertex-auth-volume
    secret:
      secretName: vertex-auth
extraVolumeMounts:
  - name: vertex-auth-volume
    mountPath: "/auth"
    readOnly: true
```

## Setup Instructions

1. Install this tool in your workspace by copying `gemini_omni_video.py` into your OpenWebUI Tools section.
2. Click the **Valves** button for this tool.
3. Enter your Google Cloud **Project ID**.
4. Enter your **Location ID** (usually `global` or `us-central1`).
5. Enable the tool for your favorite LLM and start generating!

## OpenWebUI Hub

You can also find and easily import this tool directly from the OpenWebUI Hub: [Gemini Omni Video on OpenWebUI Hub](https://openwebui.com/posts/3be427d9-766d-4e67-93e4-fab208b9340e)

## Advanced Usage Features

### Image-to-Video Generation

You can provide an image for Omni to use as the starting frame or context for your video:

- **Direct Upload**: Click the `+` attachment button in your OpenWebUI chat window to upload an image. The tool will automatically detect it and pass it to Gemini Omni.
- **URL Link**: Paste a public URL of an image directly into your prompt.

### Video-to-Video Editing

You can provide an existing video for Omni to edit (e.g. "replace the background", "make it look like a cartoon"):

- **Direct Upload (Short videos)**: Attach a short video file in OpenWebUI.
- **GCS URI (Long/Large videos)**: Since the platform has strict payload limits for inline bytes, for larger videos, upload the video to a Google Cloud Storage bucket and provide the `gs://your-bucket-name/video.mp4` link in your chat prompt. The tool will seamlessly hand it off!

## 💡 Gemini Omni Flash Prompting Guide

To get the most out of Gemini Omni Flash, here are a few tips and tricks straight from the official API documentation:

### 🎬 Scene & Camera Control

By default, Omni will try to create a video with a few different shots and cuts to craft a narrative.
If you need a single scene, explicitly prompt for it using phrases like:

- *"In a single unbroken scene"*
- *"In a single continuous shot"*
- *"No scene cuts"*

### ✂️ Editing Best Practices

Simple prompts work best for video editing. Overly descriptive prompts can lead to unintended changes across the whole video.
Always include **"Keep everything else the same"** to maintain visual consistency.

- **Avoid**: "In the video of the man sitting on the sofa, please add a small black cat that runs from the right side..."
- **Simplify**: "Add a cat that jumps onto his lap, he begins to pet it. Keep everything else the same."

### 🎵 Audio Prompting

By default, the model will generate an appropriate audio track. If you want something specific, just describe it!

- *"Include calm background music"*
- *"The video has a high energy techno beat"*

### ⏱️ Timing Events

You can prompt for things to happen at specific times using natural language or timecodes:

- *"After 3 seconds, a woman enters the scene."*
- *"Every 2s cut to a new frame."*
- `[0-3s] A person is walking`
- `[3-6s] They stop and turn around`

### 🔤 Text in Videos

Omni can render correct and readable text! Just define what it should say:

- *"There is a street sign that says: 'Omni Flash'"*
- *"One word on the screen at a time: 'did, you, know...' Each word appears for 1s. No dialogue."*

### 🖼️ Image Roles (Advanced)

If you provide multiple images in your prompt, you can use tags to tell the model exactly how to use them:

- `<FIRST_FRAME>`: Uses the image as the exact starting frame of the video.
- `<IMAGE_REF_0>`: Uses the first image as a reference (e.g. for character or style).

*Example*: `[0-3s] A studio fashion sequence. Starting with woman <IMAGE_REF_0>, she is holding <IMAGE_REF_1>`
