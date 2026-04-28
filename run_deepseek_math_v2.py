#!/usr/bin/env python3
"""
Send a repository prompt to a DeepSeek-Math-V2 compatible chat endpoint.

The script uses the OpenAI-compatible /v1/chat/completions API exposed by
servers such as vLLM or SGLang, and by many hosted inference services.
"""

import argparse
import ctypes
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from ctypes import wintypes


DEFAULT_MODEL = "deepseek-ai/DeepSeek-Math-V2"
DEFAULT_BASE_URL = "http://localhost:8000/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-v3.2-exp"
DEFAULT_CREDENTIAL_TARGET = "eq677/openrouter-api-key"
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2


class Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run PROOF_PROMPT.md against a DeepSeek-Math-V2 endpoint."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="PROOF_PROMPT.md",
        help="Prompt file to send. Defaults to PROOF_PROMPT.md.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL"),
        help=f"OpenAI-compatible base URL. Defaults to {DEFAULT_BASE_URL}, or {OPENROUTER_BASE_URL} with --openrouter.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL"),
        help=f"Model name to request. Defaults to {DEFAULT_MODEL}, or {OPENROUTER_MODEL} with --openrouter.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"),
        help="API key. Defaults to OPENAI_API_KEY, DEEPSEEK_API_KEY, Windows Credential Manager, or 'local' for localhost.",
    )
    parser.add_argument(
        "--openrouter",
        action="store_true",
        help="Use OpenRouter defaults: base URL and deepseek/deepseek-v3.2-exp model.",
    )
    parser.add_argument(
        "--credential-target",
        default=os.environ.get("OPENAI_CREDENTIAL_TARGET", DEFAULT_CREDENTIAL_TARGET),
        help=f"Windows Credential Manager target. Defaults to {DEFAULT_CREDENTIAL_TARGET}.",
    )
    parser.add_argument(
        "--save-api-key",
        action="store_true",
        help="Prompt for an API key and save it to Windows Credential Manager.",
    )
    parser.add_argument(
        "--delete-api-key",
        action="store_true",
        help="Delete the saved API key from Windows Credential Manager.",
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the response and write tokens incrementally.",
    )
    parser.add_argument(
        "--system",
        default="You are a careful mathematical proof assistant. Follow the user's requested format exactly.",
        help="System message to send before the prompt file.",
    )
    parser.add_argument(
        "--out",
        help="Optional output file. If omitted, the response is printed to stdout.",
    )
    return parser.parse_args()


def require_windows_credentials():
    if os.name != "nt":
        raise RuntimeError("Windows Credential Manager support is only available on Windows.")
    advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    advapi32.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(Credential))]
    advapi32.CredReadW.restype = wintypes.BOOL
    advapi32.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
    advapi32.CredWriteW.restype = wintypes.BOOL
    advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    advapi32.CredDeleteW.restype = wintypes.BOOL
    advapi32.CredFree.argtypes = [ctypes.c_void_p]
    advapi32.CredFree.restype = None
    return advapi32


def read_saved_api_key(target):
    if os.name != "nt":
        return None
    advapi32 = require_windows_credentials()
    credential_ptr = ctypes.POINTER(Credential)()
    if not advapi32.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(credential_ptr)):
        return None
    try:
        credential = credential_ptr.contents
        blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        return blob.decode("utf-16le")
    finally:
        advapi32.CredFree(credential_ptr)


def save_api_key(target, api_key):
    advapi32 = require_windows_credentials()
    blob = api_key.encode("utf-16le")
    blob_buffer = ctypes.create_string_buffer(blob)
    credential = Credential()
    credential.Type = CRED_TYPE_GENERIC
    credential.TargetName = target
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE
    credential.UserName = "openrouter"
    if not advapi32.CredWriteW(ctypes.byref(credential), 0):
        raise ctypes.WinError(ctypes.get_last_error())


def delete_api_key(target):
    advapi32 = require_windows_credentials()
    if not advapi32.CredDeleteW(target, CRED_TYPE_GENERIC, 0):
        error_code = ctypes.get_last_error()
        if error_code != 1168:
            raise ctypes.WinError(error_code)


def resolve_args(args):
    if args.openrouter:
        args.base_url = args.base_url or OPENROUTER_BASE_URL
        args.model = args.model or OPENROUTER_MODEL
    else:
        args.base_url = args.base_url or DEFAULT_BASE_URL
        args.model = args.model or DEFAULT_MODEL

    if not args.api_key:
        args.api_key = read_saved_api_key(args.credential_target)
    if not args.api_key:
        if args.base_url.startswith("http://localhost") or args.base_url.startswith("http://127.0.0.1"):
            args.api_key = "local"
        else:
            raise RuntimeError(
                "No API key found. Set OPENAI_API_KEY, pass --api-key, or run "
                f"`python run_deepseek_math_v2.py --save-api-key --credential-target {args.credential_target}`."
            )


def read_text(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def endpoint_url(base_url):
    return base_url.rstrip("/") + "/chat/completions"


def build_request(args, prompt):
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": prompt},
        ],
        "temperature": args.temperature,
        "top_p": args.top_p,
        "max_tokens": args.max_tokens,
    }
    if args.stream:
        payload["stream"] = True

    return urllib.request.Request(
        endpoint_url(args.base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {args.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )


def request_completion(args, prompt):
    request = build_request(args, prompt)

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {args.base_url}: {details}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach {args.base_url}: {error.reason}") from error


def stream_completion(args, prompt):
    chunks = []
    output_file = None
    if args.out:
        parent = os.path.dirname(args.out)
        if parent:
            os.makedirs(parent, exist_ok=True)
        output_file = open(args.out, "w", encoding="utf-8")

    try:
        request = build_request(args, prompt)
        with urllib.request.urlopen(request, timeout=600) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                event = line[5:].strip()
                if event == "[DONE]":
                    break
                try:
                    payload = json.loads(event)
                except json.JSONDecodeError:
                    continue
                choices = payload.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}
                text = delta.get("content") or choice.get("text") or ""
                if not text:
                    continue
                chunks.append(text)
                if output_file:
                    output_file.write(text)
                    output_file.flush()
                else:
                    print(text, end="", flush=True)
        if output_file:
            output_file.write("\n")
        else:
            print()
        return "".join(chunks)
    finally:
        if output_file:
            output_file.close()


def extract_message(data):
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        formatted = json.dumps(data, indent=2, ensure_ascii=False)
        raise RuntimeError(f"Unexpected response shape:\n{formatted}") from error


def main():
    args = parse_args()

    if args.save_api_key:
        api_key = getpass.getpass("OpenRouter API key: ")
        if not api_key:
            raise RuntimeError("No API key entered.")
        save_api_key(args.credential_target, api_key)
        print(f"Saved API key to Windows Credential Manager target: {args.credential_target}")
        return

    if args.delete_api_key:
        delete_api_key(args.credential_target)
        print(f"Deleted API key from Windows Credential Manager target: {args.credential_target}")
        return

    resolve_args(args)
    prompt = read_text(args.prompt)
    if args.stream:
        stream_completion(args, prompt)
        return

    data = request_completion(args, prompt)
    message = extract_message(data)

    if args.out:
        parent = os.path.dirname(args.out)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as file:
            file.write(message)
            file.write("\n")
    else:
        print(message)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)