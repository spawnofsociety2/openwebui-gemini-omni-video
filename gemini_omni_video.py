"""
title: Gemini Omni Video Generator
description: Generates videos using Google Vertex AI's new Gemini Omni Flash Preview model.
author: Antigravity
version: 2.3
requirements: google-genai, google-auth, google-cloud-storage
"""

import os
import uuid
import base64
import json
import asyncio
from typing import Optional, Callable, Awaitable
from pydantic import BaseModel, Field

class Tools:
    class Valves(BaseModel):
        PROJECT_ID: str = Field(
            default="your-gcp-project-id", 
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
        __user__: dict = {},
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
    ) -> str:
        """
        Generates a video based on the user's prompt using Gemini Omni Flash Preview.
        
        :param prompt: A detailed description of the video you want the model to generate.
        :return: A status message for the AI model to display.
        """
        try:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Authenticating with Google Cloud...", "done": False}
                })

            import google.auth
            from google import genai
            from google.genai import types

            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

            client = genai.Client(
                vertexai=True,
                project=self.valves.PROJECT_ID,
                location=self.valves.LOCATION_ID,
                credentials=credentials,
                http_options=types.HttpOptions(headers={"Api-Revision": "2026-05-20"}),
            )

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Generating video with Gemini Omni Flash (this may take a moment)...", "done": False}
                })

            def _generate():
                return client.interactions.create(
                    model='gemini-omni-flash-preview',
                    input=prompt
                )
                
            interaction = await asyncio.to_thread(_generate)

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Video generated! Saving to cache...", "done": False}
                })

            video_url = None
            
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
