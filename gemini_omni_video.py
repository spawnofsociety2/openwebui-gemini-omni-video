"""
title: Gemini Omni Video Generator
description: Generates videos using Google Vertex AI's new Gemini Omni Flash Preview model.
author: Antigravity
version: 1.0
requirements: google-genai, google-auth, google-cloud-storage
"""

import os
import uuid
import base64
import json
import asyncio
from typing import Optional, Callable, Awaitable, List, Union
from pydantic import BaseModel, Field
import urllib.request

class Tools:
    class Valves(BaseModel):
        PROJECT_ID: str = Field(
            default="your-google-cloud-project-id", 
            description="Google Cloud Project ID"
        )
        LOCATION_ID: str = Field(
            default="global", 
            description="Vertex AI Location for Omni models"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def generate_video(
        self,
        prompt: str,
        reference_image_url: Optional[str] = Field(
            default=None, 
            description="Optional URL of a reference image to use for generating the video. Use this if the user provides an image link."
        ),
        reference_video_url: Optional[str] = Field(
            default=None,
            description="Optional URL of a reference video to edit. Use this if the user provides a video link (e.g. gs:// bucket link or public URL)."
        ),
        __messages__: list = None,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
    ) -> str:
        """
        Generates a video based on the user's prompt using Gemini Omni Flash Preview.
        
        :param prompt: A detailed description of the video you want the model to generate.
        :param reference_image_url: Optional URL to an image to use as a starting frame or reference.
        :param reference_video_url: Optional URL to a video to edit.
        :return: An HTML5 video player containing the generated video, or an error message.
        """
        try:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Authenticating with Google Cloud...", "done": False}
                })

            # We import these here so they only load when the tool is called
            import google.auth
            from google import genai
            from google.genai import types

            # Grabs Application Default Credentials from the OpenWebUI container environment
            credentials, _ = google.auth.default()

            client = genai.Client(
                vertexai=True,
                project=self.valves.PROJECT_ID,
                location=self.valves.LOCATION_ID,
                credentials=credentials,
                http_options=types.HttpOptions(headers={"Api-Revision": "2026-05-20"}),
            )

            # Build the multimodal input payload
            api_input: list = [prompt]

            # 1. Check for reference image URL provided by the LLM
            if reference_image_url:
                if __event_emitter__:
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": "Downloading reference image from URL...", "done": False}
                    })
                try:
                    req = urllib.request.Request(reference_image_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        img_bytes = response.read()
                        mime_type = response.headers.get_content_type()
                        api_input.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
                except Exception as e:
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "status",
                            "data": {"description": f"Warning: Failed to fetch reference image URL: {e}", "done": False}
                        })

            # 2. Check for reference video URL provided by the LLM
            if reference_video_url:
                if reference_video_url.startswith("gs://"):
                    # Pass the GCS URI directly to Vertex AI
                    api_input.append(types.Part.from_uri(uri=reference_video_url, mime_type="video/mp4"))
                else:
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "status",
                            "data": {"description": "Downloading reference video from URL (may take a while)...", "done": False}
                        })
                    try:
                        req = urllib.request.Request(reference_video_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as response:
                            vid_bytes = response.read()
                            mime_type = response.headers.get_content_type()
                            api_input.append(types.Part.from_bytes(data=vid_bytes, mime_type=mime_type))
                    except Exception as e:
                        if __event_emitter__:
                            await __event_emitter__({
                                "type": "status",
                                "data": {"description": f"Warning: Failed to fetch reference video URL: {e}", "done": False}
                            })

            # 3. Check for uploaded image/video attachments in the user's last message (Open WebUI standard)
            if __messages__:
                last_msg = __messages__[-1]
                if isinstance(last_msg, dict) and last_msg.get('role') == 'user':
                    images = last_msg.get('images', [])
                    if images:
                        if __event_emitter__:
                            await __event_emitter__({
                                "type": "status",
                                "data": {"description": f"Processing {len(images)} attached image(s) from your message...", "done": False}
                            })
                        for attachment_uri in images:
                            if isinstance(attachment_uri, str):
                                if attachment_uri.startswith('data:image') or attachment_uri.startswith('data:video'):
                                    try:
                                        header, encoded = attachment_uri.split(',', 1)
                                        mime_type = header.split(';')[0].split(':')[1]
                                        attachment_bytes = base64.b64decode(encoded)
                                        api_input.append(types.Part.from_bytes(data=attachment_bytes, mime_type=mime_type))
                                    except Exception as e:
                                        pass

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Generating video with Gemini Omni Flash (this may take a moment)...", "done": False}
                })

            # Execute the synchronous API call in a thread pool so we don't block the async event loop
            def _generate():
                return client.interactions.create(
                    model='gemini-omni-flash-preview',
                    input=api_input
                )
                
            interaction = await asyncio.to_thread(_generate)

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Video generated! Processing payload...", "done": False}
                })

            video_markdown = None
            
            # The steps returned can be accessed via standard attributes or dict keys
            # We iterate through the interaction response looking for the video chunk
            for step in interaction.steps:
                step_type = step.get('type') if isinstance(step, dict) else getattr(step, 'type', None)
                step_content = step.get('content') if isinstance(step, dict) else getattr(step, 'content', [])
                
                if step_type == 'model_output' and step_content:
                    for part in step_content:
                        part_type = part.get('type') if isinstance(part, dict) else getattr(part, 'type', None)
                        
                        if part_type == 'video':
                            mime_type = part.get('mime_type', 'video/mp4') if isinstance(part, dict) else getattr(part, 'mime_type', 'video/mp4')
                            video_b64 = part.get('data') if isinstance(part, dict) else getattr(part, 'data', None)
                            video_uri = part.get('uri') if isinstance(part, dict) else getattr(part, 'uri', None)
                            
                            video_bytes = None
                            
                            if video_b64:
                                video_bytes = base64.b64decode(video_b64)
                            elif video_uri:
                                if __event_emitter__:
                                    await __event_emitter__({
                                        "type": "status",
                                        "data": {"description": f"Downloading video from {video_uri}...", "done": False}
                                    })
                                from google.cloud import storage
                                bucket_name, blob_name = video_uri[len('gs://'):].split('/', 1)
                                video_bytes = (
                                    storage.Client(credentials=credentials)
                                    .bucket(bucket_name)
                                    .blob(blob_name)
                                    .download_as_bytes()
                                )
                            
                            if video_bytes:
                                # Save the file to OpenWebUI's STATIC_DIR so it can be served unauthenticated to the HTML player
                                from open_webui.config import STATIC_DIR
                                video_id = str(uuid.uuid4())
                                
                                static_videos_dir = os.path.join(STATIC_DIR, "videos")
                                os.makedirs(static_videos_dir, exist_ok=True)
                                
                                file_path = os.path.join(static_videos_dir, f"{video_id}.mp4")
                                with open(file_path, "wb") as f:
                                    f.write(video_bytes)
                                
                                # OpenWebUI serves STATIC_DIR directly at /static/
                                video_url = f"/static/videos/{video_id}.mp4"
                                break
                    if video_url:
                        break

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Video successfully loaded!", "done": True}
                })

            if video_url:
                from fastapi.responses import HTMLResponse
                
                video_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                  body, html {{ margin: 0; padding: 0; overflow: hidden; background: transparent; }}
                </style>
                </head>
                <body>
                <div style="width:100%;max-width:1000px;margin:0 auto;margin-bottom:1rem;">
                  <video controls autoplay loop style="width:100%;aspect-ratio:16/9;background:#000;border-radius:8px;box-shadow:0 4px 15px rgba(0,0,0,0.3);">
                    <source src="{video_url}" type="video/mp4">
                    Your browser does not support the video tag.
                  </video>
                  <a href="{video_url}" target="_blank" style="display:block;margin-top:8px;font-family:sans-serif;font-size:0.9em;color:#888;text-align:center;text-decoration:none;">↓ Download Video</a>
                </div>
                <script>
                  function reportHeight() {{
                    const h = document.documentElement.scrollHeight;
                    parent.postMessage({{ type: 'iframe:height', height: h }}, '*');
                  }}
                  window.addEventListener('load', reportHeight);
                  new ResizeObserver(reportHeight).observe(document.body);
                </script>
                </body>
                </html>
                """.strip()

                return (
                    HTMLResponse(
                        content=video_html,
                        media_type="text/html",
                        headers={"content-disposition": "inline"}
                    ),
                    "Video generated and natively embedded in the chat! Tell the user to enjoy the video."
                )
            else:
                return "The model completed the request but did not return a video. It might have decided to return text instead."

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"Error: {str(e)}", "done": True}
                })
            return f"Failed to generate video: {str(e)}"
