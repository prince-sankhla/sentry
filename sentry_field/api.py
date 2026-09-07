from __future__ import annotations
import os, time
from collections import deque
from threading import Lock
from typing import Generator
from urllib.parse import urlparse
import cv2
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from .vision.config import CAPABILITY_ALIASES, DEFAULT_CONFIG, build_config
from .vision.scanner import FieldScanner
DEFAULT_CAMERA_URL=os.getenv("SENTRY_CAMERA_URL",DEFAULT_CONFIG.source)
app=FastAPI(title="SENTRY FIELD Local Gateway",version="0.3.1")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
_lock=Lock();_state={"running":False,"camera_url":DEFAULT_CAMERA_URL,"fps":0.0,"inference_ms":0.0,"findings":0,"evidence":0,"last_detection":None,"last_identity":None,"last_error":None,"updated_at":None,"mission_id":None,"requirement_id":None,"capabilities":[],"confidence":DEFAULT_CONFIG.confidence,"every_n_frames":DEFAULT_CONFIG.every_n_frames,"gps":{"status":"unavailable","source":None,"lat":None,"lon":None},"stop_token":0};_events:deque[dict]=deque(maxlen=100)
def _camera(value:str|None)->str:
 url=(value or DEFAULT_CAMERA_URL).strip();p=urlparse(url)
 if p.scheme not in {"http","https"} or not p.netloc:raise HTTPException(400,"Camera URL must be a valid http(s) URL")
 return url
def _caps(values:list[str]|None)->list[str]:
 allowed=set(CAPABILITY_ALIASES.values())
 if not values:return list(allowed)
 out=[]
 for v in values:
  v=v.strip()
  if v in allowed and v not in out:out.append(v)
 if not out:raise HTTPException(400,"No valid capabilities selected")
 return out
def _set(**u):
 with _lock:_state.update(u);_state["updated_at"]=time.time()
def _snap():
 with _lock:s=dict(_state);s.pop("stop_token",None)
 s["recent_events"]=list(_events);return s
@app.get("/health")
def health():return JSONResponse({"ok":True,"service":"sentry-field","camera_url":DEFAULT_CAMERA_URL})
@app.get("/capabilities")
def capabilities():return JSONResponse({"capabilities":[{"label":k,"value":v} for k,v in CAPABILITY_ALIASES.items()]})
@app.get("/status")
def status():return JSONResponse(_snap())
@app.get("/events")
def events():return JSONResponse({"events":list(_events)})
@app.post("/stop")
def stop():
 with _lock:_state["stop_token"]+=1;_state["running"]=False;_state["updated_at"]=time.time()
 return JSONResponse({"ok":True,"stopped":True})
def _stream(camera_url:str,confidence:float,every_n_frames:int,mission_id:str|None,requirement_id:str|None,capabilities:list[str])->Generator[bytes,None,None]:
 config=build_config(source=camera_url,confidence=confidence,every_n_frames=every_n_frames,mission_id=mission_id,requirement_id=requirement_id,capabilities=capabilities);scanner=FieldScanner(config);cap=cv2.VideoCapture(camera_url);cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
 if not cap.isOpened():_set(running=False,last_error=f"Could not open camera: {camera_url}");raise RuntimeError(f"Could not open video source: {camera_url}")
 _events.clear()
 with _lock:_state["stop_token"]+=1;token=_state["stop_token"]
 _set(running=True,camera_url=camera_url,last_error=None,mission_id=mission_id,requirement_id=requirement_id,capabilities=capabilities,confidence=config.confidence,every_n_frames=config.every_n_frames,gps={"status":"unavailable","source":None,"lat":None,"lon":None})
 idx=0;prev=time.monotonic();fps=0.0
 try:
  while True:
   with _lock:
    if _state["stop_token"]!=token:break
   started=time.monotonic();ok,frame=cap.read()
   if not ok:_set(running=False,last_error="Camera frame read failed");break
   idx+=1;detections,context,qr,barcode,ocr,persisted=scanner.scan(frame,idx);display=frame.copy()
   for d in detections:
    x1,y1,x2,y2=d.bbox;cv2.rectangle(display,(x1,y1),(x2,y2),(255,0,0),2);cv2.putText(display,f"{d.label} {d.confidence:.2f}",(x1,max(22,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,0,0),2)
    _events.appendleft({"type":d.label,"confidence":round(d.confidence,3),"bbox":d.bbox,"detector":d.detector,"track_id":d.track_id,"observed_at":time.time(),"mission_id":mission_id,"requirement_id":requirement_id})
   for item in persisted:
    event=dict(item);event["type"]="evidence";_events.appendleft(event)
   ids=[v for v in (qr,barcode,ocr) if v]
   if ids:_events.appendleft({"type":"identity","value":" | ".join(ids)[:200],"detector":"qr/barcode/ocr","observed_at":time.time(),"mission_id":mission_id,"requirement_id":requirement_id})
   now=time.monotonic();dt=now-prev;prev=now
   if dt>0:fps=.9*fps+.1*(1/dt)
   ms=(time.monotonic()-started)*1000
   with _lock:_state.update({"fps":round(fps,1),"inference_ms":round(ms,1),"findings":len(detections),"evidence":len(_events),"last_detection":{"type":detections[0].label,"confidence":round(detections[0].confidence,3),"track_id":detections[0].track_id} if detections else _state.get("last_detection"),"last_identity":" | ".join(ids)[:200] if ids else _state.get("last_identity"),"updated_at":time.time()})
   cv2.rectangle(display,(0,0),(min(display.shape[1],900),44),(15,18,25),-1);cv2.putText(display,f"SENTRY FIELD | FPS {fps:.1f} | {ms:.0f}ms | findings {len(detections)}",(14,28),cv2.FONT_HERSHEY_SIMPLEX,.62,(255,255,255),2)
   if ids:cv2.putText(display,f"ID: {' | '.join(ids)[:110]}",(14,70),cv2.FONT_HERSHEY_SIMPLEX,.48,(0,255,0),2)
   ok,enc=cv2.imencode('.jpg',display,[int(cv2.IMWRITE_JPEG_QUALITY),82])
   if ok:yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n"+enc.tobytes()+b"\r\n"
 except Exception as exc:_set(running=False,last_error=str(exc));raise
 finally:
  cap.release()
  with _lock:
   if _state["stop_token"]==token:_state["running"]=False
  _set()
@app.get("/stream")
def stream(camera_url:str|None=Query(None),confidence:float=Query(DEFAULT_CONFIG.confidence,ge=.05,le=.99),every_n_frames:int=Query(DEFAULT_CONFIG.every_n_frames,ge=1,le=60),mission_id:str|None=Query(None),requirement_id:str|None=Query(None),capabilities:str|None=Query(None)):
 return StreamingResponse(_stream(_camera(camera_url),confidence,every_n_frames,mission_id,requirement_id,_caps(capabilities.split(',') if capabilities else None)),media_type="multipart/x-mixed-replace; boundary=frame",headers={"Cache-Control":"no-store","Pragma":"no-cache"})
