import json
import numpy as np
from materials import Material        # <-- no ATLAS_Round_One.
from bands import resample_bands      # <-- direct file imports


class MaterialDB:
    def __init__(self, native_bands, items):
        self.native_bands = native_bands
        self.items = items

    @classmethod
    def from_json(cls, path):
        data = json.load(open(path, "r", encoding="utf-8"))
        bands = np.array(data["_meta"]["bands_hz"], float)
        items = {}
        for name, rec in data["materials"].items():
            alpha = np.array(rec.get("alpha", []), float)
            scatter = np.array(rec.get("scatter", [0]*len(alpha)), float)
            items[name] = Material(
                name=name, freqs=bands,
                alpha=alpha,
                tau=np.zeros_like(alpha),
                scatter=scatter,
                kind=rec.get("kind","generic")
            )
        return cls(native_bands=bands, items=items)

    def to_bands(self, dst_freqs):
        out = {}
        for n, m in self.items.items():
            a = resample_bands(m.freqs, m.alpha, dst_freqs)
            s = resample_bands(m.freqs, m.scatter, dst_freqs)
            out[n] = Material(
                name=n, freqs=dst_freqs, alpha=a,
                tau=np.zeros_like(a), scatter=s, kind=m.kind
            )
        return out
