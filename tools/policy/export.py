"""Write a trained candidate net (train.py's .pt) as plain JSON the Rust engine loads: data/learned/<name>.json."""
import json, sys
import torch
src, out = sys.argv[1], sys.argv[2]
d = torch.load(src, map_location="cpu", weights_only=False)   # our own file
sd = d["state"]
def mat(k):
    return sd[k].numpy().tolist()
head = d.get("head", "mlp")
layers = {
    "pos1_w": mat("pos.0.weight"), "pos1_b": mat("pos.0.bias"), "pos2_w": mat("pos.2.weight"), "pos2_b": mat("pos.2.bias"),
    "act1_w": mat("act.0.weight"), "act1_b": mat("act.0.bias"),
}
if head == "mlp":
    layers.update({"head1_w": mat("head.0.weight"), "head1_b": mat("head.0.bias"), "head2_w": mat("head.2.weight"), "head2_b": mat("head.2.bias")})
else:
    layers.update({"bias_w": mat("bias.weight"), "bias_b": mat("bias.bias")})
json.dump({"kind": "candidate_net", "head": head, "pos_n": d["pos_n"], "act_n": d["act_n"], "hidden": d["hidden"],
           "tag": d.get("tag"), "held_out": {k: float(v) for k, v in (d.get("held_out") or {}).items()}, **layers}, open(out, "w"))
print("wrote", out, "hidden", d["hidden"], "pos_n", d["pos_n"], "act_n", d["act_n"])
