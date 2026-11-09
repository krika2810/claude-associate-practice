import json, sys, os, hashlib, subprocess, glob, shutil
S = "/tmp/claude-0/-home-user-claude-associate-practice/ca26c6f2-af66-5743-b02d-2a231aadf0cb/scratchpad"
story = json.load(open("/home/user/claude-associate-practice/documentary/story.json"))
who, img = sys.argv[1], sys.argv[2]
c = story["cast"][who]
out = f"{S}/talk/clips/{who.lower()}"; os.makedirs(out, exist_ok=True)
n = 0
for b in story["beats"]:
    if b["shot"] != f"int_{who.lower()}": continue
    for ln in b.get("lines", []):
        key = hashlib.sha1(f"{ln['text']}|{c['voice']}|{c['speed']}".encode()).hexdigest()[:16]
        dst = f"{out}/{key}.mp4"
        if os.path.exists(dst): continue
        wav = f"{S}/build/tts/{key}.wav"
        res = f"{S}/talk/tmp_{key}"
        subprocess.run(["python3", "inference.py", "--driven_audio", wav, "--source_image", img, "--result_dir", res, "--still", "--preprocess", "full", "--size", "256", "--cpu"], cwd=f"{S}/talk/SadTalker", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        vids = sorted(glob.glob(f"{res}/*.mp4"))
        if vids: shutil.move(vids[-1], dst); n += 1; print("done", who, ln["text"][:40], flush=True)
        else: print("FAILED", who, ln["text"][:40], flush=True)
        shutil.rmtree(res, ignore_errors=True)
print("finished", who, n, flush=True)
