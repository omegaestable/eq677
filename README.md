eq677
=====

A couple of things to solve the single remaining finite implication 677 -> 255 of the [Equational Theories](https://teorth.github.io/equational_theories/) project.

The most interesting thing so far is a model searcher written for magmas satisfying 677.

There is now an archived failed route for the finite implication in [finite_e677_implies_e255_proof.md](finite_e677_implies_e255_proof.md); the current validated theorem status remains open.

Using DeepSeek-Math-V2
----------------------

DeepSeek-Math-V2 is distributed as a large DeepSeek-V3.2-Exp-based model, so the practical local path is a multi-GPU vLLM/SGLang-style server rather than direct laptop inference. The Hugging Face model card currently does not provide a hosted inference provider by default.

This repo includes a small OpenAI-compatible endpoint runner:

```powershell
python run_deepseek_math_v2.py PROOF_PROMPT.md --out outputs/deepseek-proof.md
```

By default it calls `http://localhost:8000/v1/chat/completions` with model `deepseek-ai/DeepSeek-Math-V2`. To use a hosted or remote endpoint:

```powershell
$env:OPENAI_BASE_URL = "https://your-endpoint.example/v1"
$env:OPENAI_API_KEY = "your-api-key"
$env:OPENAI_MODEL = "deepseek-ai/DeepSeek-Math-V2"
python run_deepseek_math_v2.py PROOF_PROMPT.md --out outputs/deepseek-proof.md
```

For local serving, follow the upstream DeepSeek-V3.2-Exp inference instructions for vLLM or SGLang, then run the same command once the server exposes an OpenAI-compatible `/v1` endpoint.

OpenRouter
----------

OpenRouter works with this runner, but as of 2026-04-27 its model catalog rejects the exact Hugging Face model id `deepseek-ai/DeepSeek-Math-V2`. The tested OpenRouter fallback is `deepseek/deepseek-v3.2-exp`, which is in the same DeepSeek-V3.2-Exp family.

To save the OpenRouter key in Windows Credential Manager:

```powershell
python run_deepseek_math_v2.py --save-api-key
```

After that, use OpenRouter without setting `OPENAI_API_KEY` each time:

```powershell
python run_deepseek_math_v2.py PROOF_PROMPT.md --openrouter --out outputs/deepseek-v3.2-exp-proof.md --stream
```

For a quick connectivity check before a long proof run:

```powershell
python run_deepseek_math_v2.py outputs/openrouter-smoke-prompt.md --openrouter --out outputs/openrouter-smoke-response.md --max-tokens 32 --temperature 0
```

To remove the saved key:

```powershell
python run_deepseek_math_v2.py --delete-api-key
```

Do not commit API keys. If a key was pasted into chat or terminal output, rotate it in the OpenRouter dashboard after the run.
