#!/usr/bin/env bash
# wif where [--json] [cwd] — what this directory resolves to. Always exits 0.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
json=0; cwd=$PWD
for a in "$@"; do case "$a" in --json) json=1 ;; *) cwd=$a ;; esac; done
wif_resolve "$cwd"
bind=0; wif_bindable && bind=1
status=""; [ -n "$WIF_STREAM" ] && [ -f "$WIF_STREAM" ] && status=$(wif_fm_get "$WIF_STREAM" status)
if [ $json = 1 ]; then
  jq -n --arg account "$WIF_ACCOUNT" --arg scope "$WIF_SCOPE" --arg root "$WIF_ROOT" \
    --argjson served "$WIF_SERVED" --arg kind "$WIF_KIND" --arg id "$WIF_ID" --arg path "$WIF_PATH" \
    --arg ledger "$WIF_LEDGER" --arg stream "$WIF_STREAM" --argjson bindable "$bind" --arg status "$status" \
    --arg config "$WIF_CONFIG_DIR" --arg skill "$WIF_SKILL_DIR" \
    '{account:$account, scope:$scope, root:$root, served:($served==1), kind:$kind, id:$id, path:$path,
      ledger:$ledger, stream_file:$stream, stream_exists:($status!=""), status:$status, bindable:($bindable==1),
      config_dir:$config, skill_dir:$skill}'
else
  echo "account: $WIF_ACCOUNT   scope: $WIF_SCOPE   served: $([ "$WIF_SERVED" = 1 ] && echo yes || echo NO)"
  echo "ledger:  $WIF_LEDGER"
  if [ "$WIF_KIND" = none ]; then echo "backing: none (not a herdr container, not a git repo)"
  else echo "backing: $WIF_KIND $WIF_ID  ($WIF_PATH)"; echo "stream:  ${status:-untracked}  $WIF_STREAM"; fi
fi
