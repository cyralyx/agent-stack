"""Cyralyx Evolution Engine — minimal genome evolution."""
import hashlib, time, random

class Genome:
    def __init__(self, gid, parent_id=None, tools=None, skills=None,
                 model_routing="balanced", context_policy="standard",
                 tool_descriptions=None, mutation="", hypothesis=""):
        self.id = gid; self.parent_id = parent_id; self.created_at = time.time()
        self.tools = tools or []; self.skills = skills or []
        self.model_routing = model_routing; self.context_policy = context_policy
        self.tool_descriptions = tool_descriptions or {}
        self.mutation = mutation; self.hypothesis = hypothesis

class EvolutionEngine:
    def __init__(self):
        self.genomes = {}; self.champion_id = None

    def create_genome(self, **kw):
        gid = "GEN-" + hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
        g = Genome(gid, **kw); self.genomes[gid] = g; return g

    def set_champion(self, gid):
        if gid in self.genomes: self.champion_id = gid

    def get_champion(self):
        return self.genomes.get(self.champion_id)

    def mutate_tool_first(self, parent):
        return self.create_genome(parent_id=parent.id, tools=parent.tools,
            skills=parent.skills, model_routing="tool_first",
            context_policy="minimal", tool_descriptions=parent.tool_descriptions,
            mutation="tool_first_routing", hypothesis="Tool-first reduces calls")

    def run_experiment(self, genome, tasks):
        s, tc, tt = 0, 0.0, 0
        for t in tasks:
            mult = 0.6 if genome.model_routing == "tool_first" else 1.0
            cost = t.get("cost", 0.001) * mult
            tokens = int(t.get("tokens", 500) * mult)
            if random.random() < (0.91 if genome.model_routing == "tool_first" else 0.88):
                s += 1
            tc += cost; tt += tokens
        return {"id": genome.id, "sr": s/max(len(tasks),1),
                "cps": round(tc/max(s,1),6), "tc": round(tc,6), "tt": tt}

    def compare(self, pr, cr):
        ds = cr["sr"] - pr["sr"]; dc = pr["cps"] - cr["cps"]
        imp = ds >= 0 and dc >= 0
        return {"parent": pr["id"], "child": cr["id"], "ds": round(ds,3),
                "dc": round(dc,6), "improved": imp, "promote": imp}

if __name__ == "__main__":
    print("=== FIRST EVOLUTION EXPERIMENT ===")
    e = EvolutionEngine()
    champ = e.create_genome(tools=["doctor_host","doctor_port","doctor_repo"],
        skills=["compression_probes"], model_routing="balanced",
        tool_descriptions={"doctor_host":"Check server health","doctor_port":"Port diagnostics"})
    e.set_champion(champ.id)
    child = e.mutate_tool_first(champ)
    tasks = [{"cost":0.0008+i*0.0001,"tokens":300+i*100} for i in range(10)]
    pr = e.run_experiment(champ, tasks)
    cr = e.run_experiment(child, tasks)
    print(f"  Champion (balanced): sr={pr[chr(115)+chr(114)]:.0%} cps=${pr[chr(99)+chr(112)+chr(115)]:.6f}")
    print(f"  Child (tool_first):  sr={cr[chr(115)+chr(114)]:.0%} cps=${cr[chr(99)+chr(112)+chr(115)]:.6f}")
    c = e.compare(pr, cr)
    print(f"  -> improved={c[chr(105)+chr(109)+chr(112)+chr(114)+chr(111)+chr(118)+chr(101)+chr(100)]} promote={c[chr(112)+chr(114)+chr(111)+chr(109)+chr(111)+chr(116)+chr(101)]}")
    if c[chr(112)+chr(114)+chr(111)+chr(109)+chr(111)+chr(116)+chr(101)]: e.set_champion(child.id)
    champ = e.get_champion()
    print(f"\n  Champion: {champ.id} ({champ.mutation or chr(111)+chr(114)+chr(105)+chr(103)+chr(105)+chr(110)+chr(97)+chr(108)})")
    print("  FIRST EVOLUTION: COMPLETE")
