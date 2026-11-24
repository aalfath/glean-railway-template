#!/bin/sh
# Railway: resolve the backend through Railway's DNS at request time (so a
# redeployed backend is found again) and size nginx workers to the service's CPUs.
set -eu
: "${BACKEND_URL:?BACKEND_URL is required, e.g. http://backend.railway.internal:8000}"
ns=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)
case "$ns" in *:*) ns="[$ns]" ;; esac
echo "resolver ${ns:-127.0.0.11} ipv6=on valid=10s;" > /etc/nginx/conf.d/00-resolver.conf
cpus=1
if [ -r /sys/fs/cgroup/cpu.max ]; then
  read -r quota period < /sys/fs/cgroup/cpu.max || true
  if [ "${quota:-max}" != "max" ] && [ -n "${period:-}" ]; then cpus=$(( (quota + period - 1) / period )); else cpus=2; fi
fi
[ "$cpus" -lt 1 ] && cpus=1; [ "$cpus" -gt 4 ] && cpus=4
sed -i "s/^worker_processes.*/worker_processes $cpus;/" /etc/nginx/nginx.conf
