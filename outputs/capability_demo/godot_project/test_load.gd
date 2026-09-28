extends SceneTree

func _init():
    if not FileAccess.file_exists("res://assets/world.glb"):
        print("FAIL: world.glb missing")
        quit(1)
        return
    var s = load("res://assets/world.glb")
    print("OK world.glb loaded as: ", s.get_class())
    if s is PackedScene:
        var i = s.instantiate()
        if i:
            print("OK instantiated: ", i.get_class())
            print("  child nodes: ", _count(i))
    quit(0)

func _count(n) -> int:
    var c = 1
    for child in n.get_children():
        c += _count(child)
    return c
