# Few-shots

## 1. Happy path

Input: `Remember we terminate TLS at Envoy and keep app pods HTTP-only.`

Tool sequence:

```bash
scripts/memory --cwd . root
scripts/memory --cwd . classify --text "Terminate TLS at Envoy; app pods HTTP-only" --hint "architecture decision" --title "edge-tls"
scripts/memory --cwd . slug "edge-tls"
scripts/memory --cwd . write user/edge-tls.md --content "# Edge TLS

Terminate TLS at Envoy. App pods stay HTTP-only.
"
scripts/memory --cwd . index-link --scope user --slug edge-tls --filename edge-tls.md --summary "TLS terminates at Envoy"
scripts/memory --cwd . read user/edge-tls.md
```

Expected telemetry (shape):

```json
{
  "ok": true,
  "skill": "memory-system",
  "op": "write",
  "scope": "user",
  "path": "user/edge-tls.md",
  "confidence": 1.0,
  "next": ["recall", "update", "promote-to-skill", "copy-to-team"]
}
```

Human recap: saved as `user/edge-tls.md` and linked from `user/MEMORY.md`.

## 2. Adversarial / malformed

Input: `Remember this: api_key="sk-ant-abcdefghijklmnopqrstuvwxyz123456"`

```bash
scripts/memory scan-secrets --text 'api_key="sk-ant-abcdefghijklmnopqrstuvwxyz123456"'
scripts/memory --cwd . write user/keys.md --content 'api_key="sk-ant-abcdefghijklmnopqrstuvwxyz123456"'
```

Expected: exit `3`, `"ok": false`, `"error": {"code": "secret_detected"}`.

Correct behavior: refuse. Tell the human the payload matched a secret rule. Do not store a redacted variant unless they provide a non-secret note ("API keys live in 1Password, not the repo").

Path injection input: `read ../etc/passwd` → `"ok": false`. Do not retry with a "helpful" rewritten path.

## 3. Failure recovery

Mid-write, tool returns:

```json
{
  "ok": false,
  "op": "write",
  "error": {"code": "exists", "path": "user/edge-tls.md", "hint": "Read first, then pass --overwrite"}
}
```

Recovery:

1. Surface the raw error. Do not claim success.
2. `read user/edge-tls.md`
3. If the change is a surgical edit, `edit --old … --new …`
4. If the human confirmed a full replace in this turn, `write --overwrite`
5. `read` again and match `sha256`
6. If a transient failure repeats 3×, halt and emit failure telemetry. Do not switch to bash redirection.
