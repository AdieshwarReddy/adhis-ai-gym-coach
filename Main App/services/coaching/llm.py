from services.config.workout_config import PROMPT


class LLMCoach:
    def __init__(self, groq_client=None, gemini_api_key: str = ""):
        self.client = groq_client
        self.gemini_key = gemini_api_key
        self.history = []
        self.system_prompt = PROMPT

    def _call_gemini(self, user_prompt: str) -> str:
        """Query Google Gemini 2.5 Flash API via REST."""
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": self.system_prompt}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]}
            ]
        }
        res = requests.post(url, json=payload, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        return ""

    def _deterministic_fallback(self, event, issue):
        if issue:
            issue_lower = issue.lower()
            if "elbow" in issue_lower or "drift" in issue_lower:
                return "Keep your elbows stable and close to your body."
            if "swing" in issue_lower or "torso" in issue_lower:
                return "Brace your core and eliminate torso swing."
            if "deep" in issue_lower or "depth" in issue_lower:
                return "Go deeper into your squat for full range of motion."
            if "lean" in issue_lower or "forward" in issue_lower:
                return "Keep your chest up and torso upright."
            if "hip" in issue_lower or "sag" in issue_lower or "pike" in issue_lower:
                return "Align your hips and keep your body in a straight line."
            if "balance" in issue_lower:
                return "Widen your stance slightly and maintain balance."
            if "arch" in issue_lower:
                return "Avoid arching your lower back. Engage your core."
            if "frame" in issue_lower or "camera" in issue_lower:
                return "Step into the camera frame so I can track your movement."
            return issue

        fallbacks = {
            "workout_started": "Workout started! Let's maintain great form and focus.",
            "workout_completed": "Incredible effort! You have completed your workout session.",
            "set_completed": "Set complete! Excellent control. Catch your breath.",
            "no_pose_detected": "Please step into the camera view so your full body is visible.",
            "ongoing_form_check": "Great pacing, keep your movement smooth and controlled.",
        }
        return fallbacks.get(event, "Great form, keep moving with control.")

    def give_feedback(self, event, issue):
        if not self.client and not self.gemini_key:
            return self._deterministic_fallback(event, issue)

        prompt = f"Event: {event}"
        if issue:
            prompt += f" Form Issue: {issue}"

        # 1. Try Gemini if configured
        if self.gemini_key:
            try:
                text = self._call_gemini(prompt)
                if text:
                    self.history.append({"role": "assistant", "content": text})
                    return text
            except Exception:
                pass

        # 2. Try Groq if client available
        if self.client:
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self.history[-10:],
                {"role": "user", "content": prompt}
            ]
            candidate_models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "groq/compound-mini", "llama-3.3-70b-versatile"]
            for model_name in candidate_models:
                try:
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0.4,
                        timeout=5.0,
                    )
                    text = response.choices[0].message.content.strip()
                    if text:
                        self.history.append({"role": "assistant", "content": text})
                        return text
                except Exception:
                    continue

        return self._deterministic_fallback(event, issue)


    