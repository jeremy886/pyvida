# generated by ingame editor v0.1

def load_state(game, scene):
    from __init__ import WalkArea, Rect
    import os
    scene.clean(["_test_actor"])
    scene.walkareas.set([WalkArea().smart(game, [(100, 600), (900, 560), (920, 700), (80, 720)]),])
    game._test_actor.relocate(scene, (50,50))
