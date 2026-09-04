from __future__ import annotations
import json, urllib.request
from app.db import Database

class AIService:
    def __init__(self,db:Database,url:str,key:str,model:str,system_prompt:str): self.db,self.url,self.key,self.model,self.system=db,url,key,model,system_prompt
    def reply(self,uid:int,chat_id:int,prompt:str)->str:
        history=[{"role":r["role"],"content":r["content"]} for r in self.db.memory(uid,chat_id)]
        if not self.url or not self.key:
            text="I’m here. AI service is not configured yet, but the bot is ready for conversation."
            self.db.remember(uid,chat_id,"user",prompt); self.db.remember(uid,chat_id,"assistant",text)
            return text
        payload={"model":self.model,"messages":[{"role":"system","content":self.system},*history,{"role":"user","content":prompt}],"temperature":0.8}
        req=urllib.request.Request(self.url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","Authorization":f"Bearer {self.key}"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=30) as res: data=json.loads(res.read().decode())
            text=data.get("choices",[{}])[0].get("message",{}).get("content","").strip()
            if not text: raise ValueError("Empty AI response")
        except Exception:
            text="I’m having trouble reaching my AI service right now. Please try again in a moment."
        self.db.remember(uid,chat_id,"user",prompt); self.db.remember(uid,chat_id,"assistant",text)
        return text
