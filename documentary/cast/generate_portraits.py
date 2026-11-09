import sys, time, torch, json
from diffusers import StableDiffusionPipeline, AutoencoderKL, DPMSolverMultistepScheduler
torch.set_num_threads(4)
vae = AutoencoderKL.from_pretrained("stabilityai/sd-vae-ft-mse", torch_dtype=torch.float32)
pipe = StableDiffusionPipeline.from_pretrained("SG161222/Realistic_Vision_V6.0_B1_noVAE", vae=vae, torch_dtype=torch.float32, safety_checker=None, requires_safety_checker=False)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++")
pipe.set_progress_bar_config(disable=True)
jobs = json.load(open(sys.argv[1]))
NEG = "nsfw, nude, cleavage, bare legs, lying down, suggestive, woman, female, cartoon, 3d render, cgi, doll, plastic skin, painting, illustration, anime, deformed face, asymmetric eyes, extra limbs, text, watermark, logo, oversaturated, overexposed"
for j in jobs:
    t = time.time()
    g = torch.Generator().manual_seed(j["seed"])
    img = pipe(j["prompt"], negative_prompt=(NEG.replace("woman, female, ", "") if j.get("neg_extra") else NEG), width=j.get("w", 768), height=j.get("h", 512), num_inference_steps=j.get("steps", 24), guidance_scale=j.get("cfg", 5.0), generator=g).images[0]
    img.save(j["out"]); print(j["out"], round(time.time() - t, 1), "s", flush=True)
