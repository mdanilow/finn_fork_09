import json

with open("my_folding_config.json") as file:
    d = json.load(file)

# MatrixVectorActivation
mva_ramstyle_from_idx = 33
mva_ramstyle = "auto"

mva_restype_from_idx = 0
mva_restype = "dsp"

mva_memmode_from_idx = 33
mva_memmode = "external"

# VectorVectorActivation
vva_ramstyle_from_idx = 0
vva_ramstyle = "auto"

vva_restype_from_idx = 0
vva_restype = "dsp"

vva_memmode_from_idx = 0
vva_memmode = "const"


for module, module_dict in d.items():
    if("_" in module):
        module_idx = int(module.split("_")[-1])

    if("MatrixVector" in module):
        if module_idx >= mva_ramstyle_from_idx:
            module_dict["ram_style"] = mva_ramstyle
            if mva_ramstyle == "ultra":
                module_dict["runtime_writeable_weights"] = 1

        if module_idx >= mva_restype_from_idx:
            module_dict["resType"] = mva_restype

        if module_idx >= mva_memmode_from_idx:
            module_dict["mem_mode"] = mva_memmode
        
    elif("VectorVector" in module):
        if module_idx >= vva_ramstyle_from_idx:
            module_dict["ram_style"] = vva_ramstyle
            if vva_ramstyle == "ultra":
                module_dict["runtime_writeable_weights"] = 1

        if module_idx >= vva_restype_from_idx:
            module_dict["resType"] = vva_restype

        if module_idx >= vva_memmode_from_idx:
            module_dict["mem_mode"] = vva_memmode

with open('my_folding_config.json', 'w') as file:
    json.dump(d, file, indent=2)
