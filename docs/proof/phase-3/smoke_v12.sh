set -u
D=$1
h() { python3 -m chonoi.headless "$@"; }
now() { python3 -c "import time;print(time.time())"; }
echo '{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":30}],"random_fish":false,"monsters":[]}}' > $D/th.json
h --mode gather --seed 1 --scenario $D/th.json --ticks 1 --out $D/th.jsonl; echo "[ngưỡng 30] exit=$?"
grep '"spoiled"' $D/th.jsonl
echo '{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":100}],"random_fish":false,"monsters":[]}}' > $D/dock.json
echo '{"frames":[{"tick":0,"interact":true}]}' > $D/dock-in.json
h --mode gather --seed 1 --scenario $D/dock.json --inputs $D/dock-in.json --ticks 1 --out $D/g.jsonl --inventory-out $D/kho.json; echo "[bàn giao] gather exit=$?"
echo "kho.json: $(cat $D/kho.json)"
h --mode quan --seed 1 --inventory $D/kho.json --ticks 0 --out $D/q.jsonl; echo "[bàn giao] quan exit=$?"
python3 -c "import json;s=json.loads(open('$D/q.jsonl').readline());f=json.load(open('$D/kho.json'))['items'];print('quan tick0 stock:',s['stock']);print('khớp id/kind/fresh(±0.01):',len(f)==len(s['stock']) and all((a['id'],a['kind'])==(b['id'],b['kind']) and abs(a['fresh']-b['fresh'])<=0.01 for a,b in zip(s['stock'],f)))"
echo '{"items":{"ca_loc":1}}' > $D/old.json
h --mode quan --seed 1 --inventory $D/old.json --ticks 0 --out $D/x.jsonl; echo "[kho đếm v1.1] exit=$? (mong đợi 2)"
for n in 1 3; do
  s=$(now); h --mode day --days $n --seed 7 --ticks 200000 --out $D/day$n.jsonl; c=$?; e=$(now)
  echo "[day --days $n] exit=$c thời gian=$(python3 -c "print(round($e-$s,2))")s"; tail -1 $D/day$n.jsonl
done
h --mode day --days 3 --seed 7 --ticks 200000 --out $D/day3b.jsonl; cmp -s $D/day3.jsonl $D/day3b.jsonl && echo "[day] cùng seed giống từng byte"
