"""Inference script for OpenEnv benchmark."""

import json
import os

from openai import OpenAI
from dna_mutation_env.client import DnaMutationEnv
from dna_mutation_env.models import DnaMutationAction

SYSTEM_PROMPT = """
You are a genomic analysis agent operating a DNA mutation detection environment.
Return exactly one JSON object with keys:
action_type, locus, end, variant_type, ref_allele, alt_allele, confidence, reasoning.
Prefer inspect_region before a final answer when evidence is ambiguous.
""".strip()

def _extract_json(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    elif "{" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end+1]
    return cleaned

def main():
    api_base_url = os.getenv("API_BASE_URL", "http://0.0.0.0:4000")
    model_name = os.getenv("MODEL_NAME", "gpt-4.1-mini")
    hf_token = os.getenv("HF_TOKEN")
    if hf_token is None:
        raise ValueError("HF_TOKEN environment variable is required")

    client = OpenAI(base_url=api_base_url, api_key=hf_token)

    env_url = os.getenv("OPENENV_URL", "http://127.0.0.1:8000")
    env = DnaMutationEnv(base_url=env_url)
    
    seed = int(os.getenv("SEED", "42"))
    task_id = os.getenv("TASK_ID", "easy_snv_short_read")

    step_result = env.reset(seed=seed, task_id=task_id)
    observation = step_result.observation
    
    print(f"[START] task=dna-mutation env=dna-mutation-env model={model_name}", flush=True)

    step_count = 0
    reward_list = []
    success = False
    
    try:
        done = step_result.done
        while not done:
            step_count += 1
            error_msg = "null"
            action_str = "{}"
            reward_val = 0.00
            
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps({
                                "task_id": observation.task_id,
                                "difficulty": observation.difficulty,
                                "task_description": observation.task_description,
                                "reference_sequence": observation.reference_sequence,
                                "observed_sequence": observation.observed_sequence,
                                "coverage": observation.coverage,
                                "quality_scores": observation.quality_scores,
                                "candidate_regions": [
                                    r.model_dump() for r in observation.candidate_regions
                                ],
                                "prior_findings": [
                                    f.model_dump() for f in observation.prior_findings
                                ],
                                "action_budget_remaining": observation.action_budget_remaining,
                            })
                        }
                    ],
                )
                
                content = _extract_json(response.choices[0].message.content or "{}")
                action = DnaMutationAction.model_validate_json(content)
                action_str = action.model_dump_json().replace("\n", " ").strip()
                
                step_result = env.step(action)
                observation = step_result.observation
                reward_val = step_result.reward if step_result.reward is not None else 0.0
                done = step_result.done
                
            except Exception as e:
                error_msg = str(e).replace("\n", " ").strip()
                if not error_msg:
                    error_msg = repr(e)
                done = True
                
            reward_list.append(reward_val)
            done_str = "true" if done else "false"
            
            print(f"[STEP] step={step_count} action={action_str} reward={reward_val:.2f} done={done_str} error={error_msg}", flush=True)

            if done:
                if reward_val > 0.0:
                    success = True
                break
                
    except Exception as e:
        last_error = str(e)
    finally:
        if hasattr(env, "close"):
            try:
                env.close()
            except Exception:
                pass
        success_str = "true" if success else "false"
        rewards_str = ",".join(f"{r:.2f}" for r in reward_list)
        print(f"[END] success={success_str} steps={step_count} rewards={rewards_str}", flush=True)


if __name__ == "__main__":
    main()
