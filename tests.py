import unittest

from __init__ import *

RESOLUTION_X = 1000
RESOLUTION_Y = 1000
RESOLUTION = (RESOLUTION_X, RESOLUTION_Y)



class ActorTest(unittest.TestCase):
    def setUp(self):
        self.game = Game("Unit Tests", fps=60, afps=16, resolution=RESOLUTION)
        self.game.settings = Settings()
        self.actor = Actor("_test_actor").smart(self.game)
        self.parent = Actor("_test_actor_parent").smart(self.game, using="data/actors/_test_actor")
        self.game.add(self.actor)

    def test_initial_xy(self):
        self.assertEqual(self.actor.x, 0)
        self.assertEqual(self.actor.y, 0)

    def test_locations(self):
        self.actor.x, self.actor.y = 100,100
        self.assertEqual(self.actor.x, 100)
        self.assertEqual(self.actor.y, 100)
        self.actor.pyglet_draw()
        self.assertEqual(self.actor._sprite.x, 100)
        self.assertEqual(self.actor._sprite.y, RESOLUTION_Y - self.actor.y - self.actor._sprite.height)

    def test_anchor(self):
        self.actor.x, self.actor.y = 100,100
        self.actor._ax, self.actor._ay = -25, -100
        self.assertEqual(self.actor._ax, -25)
        self.assertEqual(self.actor._ay, -100)

        self.actor.ax, self.actor.ay = -25, -100
        self.assertEqual(self.actor._ax, -25)
        self.assertEqual(self.actor._ay, -100)
        
        self.actor.pyglet_draw()
        self.assertEqual(self.actor._sprite.x, 75)
        self.assertEqual(self.actor._sprite.y, RESOLUTION_Y - self.actor.y - self.actor._sprite.height - self.actor.ay)


    def test_clickable_area(self):
        self.assertEqual(self.actor.clickable_area.w, 100)
        self.assertEqual(self.actor.clickable_area.h, 100)
        self.actor.x, self.actor.y = 100,100
        self.assertEqual(self.actor.clickable_area.x, 100)
        self.assertEqual(self.actor.clickable_area.y, 100)


    def test_clickable_mask(self):
        self.actor._clickable_area = Rect(0,0,100,100)

        #autogenerated mask should match clickable area
        self.assertEqual(self.actor.clickable_area.w, 100)
        self.assertEqual(self.actor.clickable_area.h, 100)

        self.assertFalse(self.actor.collide(-200,-200)) #miss
        self.assertTrue(self.actor.collide(0,0)) #hit
        self.assertTrue(self.actor.collide(50,50)) #hit
        self.assertFalse(self.actor.collide(200,200)) #miss
        self.assertFalse(self.actor.collide(300,300)) #miss


        #using reclickable resets the mask

        self.actor.on_reclickable(Rect(50,50,200,200))
        self.assertEqual(self.actor.clickable_area.w, 200)
        self.assertEqual(self.actor.clickable_area.h, 200)
        
        self.assertFalse(self.actor.collide(0,0)) #miss
        self.assertTrue(self.actor.collide(50,50)) #hit
        self.assertTrue(self.actor.collide(200,200)) #hit
        self.assertFalse(self.actor.collide(300,300)) #miss

    def test_debug_draw(self):
        self.actor.x, self.actor.y = 100,100
        self.actor._ax, self.actor._ay = -25, -100
        self.actor.show_debug = True
        self.actor.pyglet_draw() #will also draw debugs now
        self.assertEqual(len(self.actor._debugs), 4)
        position, anchor, stand, clickable_area = self.actor._debugs
        self.assertEqual(position, (100, 100))
        self.assertEqual(anchor, (75, 0))

    def test_debug_draw_clickable(self):
        self.actor.x, self.actor.y = 100,100
        self.actor.show_debug = True
        self.actor.pyglet_draw() #will also draw debugs now
        position, anchor, stand, clickable_area = self.actor._debugs
        self.assertEqual(clickable_area, [(100, 900), (200, 900), (200, 800), (100, 800)])

    def test_smart_using(self):
        msgbox = Item("msgbox").smart(self.game, using="data/items/_test_item")
        self.assertEqual(msgbox.name, "msgbox")
        self.assertEqual(msgbox.action.name, "idle")
        self.assertEqual(msgbox.w, 100)

    def test_parent(self):
        self.actor._parent = self.parent
        self.actor.x, self.actor.y = 0,0
        self.parent.x, self.parent.y = 100,100
        position = (self.actor.x, self.actor.y)
        self.assertEqual(self.actor.collide(100,100), True)
        self.assertEqual(self.actor.collide(150,150), True)


class ActorScaleTest(unittest.TestCase):
    def setUp(self):
        self.game = Game("Unit Tests", fps=60, afps=16, resolution=RESOLUTION)
        self.game.settings = Settings()
        self.actor = Actor("_test_actor").smart(self.game)
        self.actor.x, self.actor.y = 500,1000
        self.game.add(self.actor)


    def test_scale(self):
        a = self.actor
        self.assertEqual(float(a.scale), 1.0)
        self.assertEqual([a._clickable_area.w, a._clickable_area.h], [100, 100])

        a.scale = 0.5
        self.assertEqual(a.x, 500)
        self.assertEqual(a.ax, 0)
        self.assertEqual([a._clickable_area.w, a._clickable_area.h], [50,50])

        a.scale = 1.0
        a.ay = -500
        self.assertEqual(a.ay, -500)
        self.assertEqual([a._clickable_area.w, a._clickable_area.h], [100,100])

        a.scale = 0.5
        self.assertEqual(a.ay, -250)
        self.assertEqual([a._clickable_area.w, a._clickable_area.h], [50,50])


class ActorSmartTest(unittest.TestCase):
    def setUp(self):
        self.game = Game("Unit Tests", fps=60, afps=16, resolution=RESOLUTION)
        self.game.settings = Settings()

    def _generic_tests(self, actor):
        self.assertIn("idle", actor._actions.keys())
        self.assertEqual(actor.action.name, "idle")
        self.assertEqual(actor.w, 100)

    def test_smart(self):
        self.actor = Actor("_test_actor").smart(self.game)
        self._generic_tests(self.actor)

    def test_smart_using(self):
        self.actor = Actor("_test_actor").smart(self.game, using="data/actors/_test_actor")
        self._generic_tests(self.actor)

        self.actor = Actor("_test_actor").smart(self.game, using="data/items/_test_item")
        self._generic_tests(self.actor)


    def test_item_smart_using(self):
        actor = Item("msgbox").smart(self.game, using="data/items/_test_item")
        self.assertEqual(actor.name, "msgbox")
        self._generic_tests(actor)


class EventTest(unittest.TestCase):
    def setUp(self):
        self.game = Game("Unit Tests", fps=60, afps=16, resolution=RESOLUTION)
        self.game.settings = Settings()
        self.actor = Actor("_test_actor").smart(self.game)
        self.msgbox = Item("msgbox").smart(self.game, using="data/items/_test_item")
        self.ok = Item("ok").smart(self.game, using="data/items/_test_item")
        self.scene = Scene("_test_scene")
        self.game.add([self.scene, self.actor, self.msgbox, self.ok])

    def test_relocate(self):
        self.actor.relocate(self.scene)
        event = self.game._events[0]
        self.assertEqual(len(self.game._events), 1)
        self.assertEqual(event[0].__name__, "on_relocate")
        self.assertEqual(event[1][0], self.actor)
        self.assertEqual(event[1][1], self.scene)

    def test_on_says_using(self):
        self.actor.says("Hello World", using="data/items/_test_item", ok=False)
        self.assertEqual(len(self.game._events), 1)
        event = self.game._events[0]
        self.assertEqual(self.game._event, None)
        self.assertEqual(event[0].__name__, "on_says")
        self.assertEqual(event[1][0], self.actor)
        self.assertEqual(event[1][1], "Hello World")
        self.game.update(0)
        event = self.game._events[0]


    def test_event_ordering(self):
        self.actor.says("Hello World", ok=False)
        self.actor.says("Goodbye World", ok=False)
        events = self.game._events
        self.assertEqual(events[0][1][1], "Hello World")
        self.assertEqual(events[1][1][1], "Goodbye World")


    def test_on_says_events(self):
        self.actor.says("Hello World", using="data/items/_test_item", ok=False)
        self.actor.says("Goodbye World", using="data/items/_test_item", ok=False)

        self.game.update(0, single_event=True) #start the first on_says
        self.assertEqual(self.game._event_index, 1)
        self.assertEqual(self.game._waiting, True)
        self.assertEqual(self.actor._busy, True)
        self.assertEqual(len(self.game._modals), 2)

        self.game.update(0, single_event=True) #should still be blocking as user has done nothing

        self.assertEqual(self.game._event_index, 1)
        self.assertEqual(self.game._waiting, True)
        self.assertEqual(self.actor._busy, True)
        self.assertEqual(len(self.game._modals), 2)

        #finish the on_says event, the next on_says should not have started yet

        self.game._modals[0].trigger_interact() #finish the on says

        self.assertEqual(len(self.game._modals), 0) #should be gone
        self.assertEqual(self.actor._busy, False) #actor should be free
        self.assertEqual(self.game._event_index, 1) #still on first event
        self.assertEqual(self.game._waiting, True) #game still waiting

        self.game.update(0, single_event=True) #trigger the next on_says, everything should be waiting again

        self.assertEqual(self.game._event_index, 1)
        self.assertTrue(self.game._waiting)
        self.assertTrue(self.actor._busy)
        self.assertEqual(len(self.game._modals), 2)

        self.game._modals[0].trigger_interact() #finish the on says

        self.game.update(0, single_event=True) #trigger the next on_says, everything should be waiting again


        self.assertEqual(len(self.game._modals), 0)
        self.assertEqual(len(self.game._events), 0)


    def test_relocate_says_events(self):
        self.actor.relocate(self.scene, (100,100))
        self.actor.says("Hello World", ok=False)
        self.actor.relocate(self.scene, (200,200))
        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_relocate', 'on_says', 'on_relocate'])

        self.game.update(0, single_event=True) #do relocate, probably starts on_says
        self.game.update(0, single_event=True) #finish the relocate, starts on_says

        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_says', 'on_relocate'])
        self.assertEqual(self.game._event_index, 1)
        self.assertTrue(self.game._waiting) #waiting for modals to clear
        self.assertTrue(self.actor._busy) #waiting for modals to clear
        self.assertEqual(len(self.game._modals), 2) #no OK button

        #need to trip the modals
        self.game._modals[0].trigger_interact()

        self.game.update(0) #finish the on_says and start and fininsh on_relocate
        self.assertEqual(len(self.game._modals), 0) #on_says cleared
        self.assertEqual([x[0].__name__ for x in self.game._events], [])

    def test_on_asks(self):
        @answer("Hello World")
        def answer0(game, btn, player):
            self.actor.says("Hello World", ok=False)

        @answer("Goodbye World")
        def answer1(game, btn, player):
            self.actor.says("Goodbye World", ok=False)
        self.actor.asks("What should we do?", answer0, answer1, ok=False)

        self.assertEqual(len(self.game._modals), 0)

        self.game.update(0, single_event=True) #start on_asks
        self.assertEqual(len(self.game._modals), 4) #no OK button, so msgbox, statement, two options
        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_asks'])

        self.game.update(0, single_event=True) #start on_asks
        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_asks'])
 
        self.game._modals[2].trigger_interact() #first option

        self.game.update(0, single_event=True) #finish on_asks, start on_says
    
        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_says'])

        

    def test_load_state(self):
        self.actor.relocate(self.scene, (100,100))
        self.actor.says("Hello World", ok=False)
        self.game.load_state(self.scene, "initial")
        self.actor.relocate(self.scene, (200,200))
        self.menuItem = Item("menu_item")

        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_relocate', 'on_says',  'on_clean', 'on_relocate', 'on_relocate'])
        self.game.update(0, single_event=True) #do relocate, probably starts on_says
        self.game.update(0, single_event=True) #finish the relocate, starts on_says

        #need to trip the modals
        self.game._modals[0].trigger_interact()
        self.game.update(0, single_event=True) #finish the on_says and start and fininsh on_relocate

        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_clean', 'on_relocate', 'on_relocate'])

    def test_splash(self):
        self.game.hello = False

        def initial(d, game):
            """ Splash callback """
            game.hello = True
            game.camera.scene(self.scene)
            game.load_state(self.scene, "initial")    
            game.camera.scene(self.scene)
            game.set_menu("menu_item")
            game.menu.show()

        self.game.splash(None, initial)
        self.assertFalse(self.game._waiting) #nothing has happened yet
        self.assertFalse(self.game._busy)

        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_splash'])

        self.game.update(0, single_event=True) #start on_splash, callback called instantly

        self.assertTrue(self.game.hello) #callback was successful

        self.game.update(0, single_event=True)

        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_scene', 'on_clean', 'on_relocate', 'on_scene', 'on_set_menu', "on_show"])



class WalkthroughTest(unittest.TestCase):
    def setUp(self):
        self.game = Game("Unit Tests", fps=60, afps=16, resolution=RESOLUTION)
        self.game.settings = Settings()
        self.actor = Actor("_test_actor").smart(self.game)
        self.msgbox = Item("msgbox").smart(self.game, using="data/items/_test_item")
        self.ok = Item("ok").smart(self.game, using="data/items/_test_item")
        self.scene = Scene("_test_scene")
        self.game._headless = True
        self.game.add([self.scene, self.actor, self.msgbox, self.ok])
        self.game.camera._scene(self.scene)

        @answer("Hello World")
        def answer0(game, btn, player):
            self.actor.says("Hello World", ok=False)

        @answer("Goodbye World")
        def answer1(game, btn, player):
            self.actor.says("Goodbye World", ok=False)

        def interact__test_actor(game, actor, player):
            self.actor.asks("What should we do?", answer0, answer1, ok=False)
        self.actor.interact = interact__test_actor
        suites = [[
            (description, "Test Test Suite"),
            (location, "_test_scene"),
            (interact, "_test_actor"),
            (interact, "Hello World"),
        ]]
        self.game.walkthroughs(suites)

    def test_walkthrough(self):
#        self._walkthrough = []
        self._walkthrough_index = 0 #our location in the walkthrough
        self._walkthrough_target = 0  #our target
        self.assertEqual([x[0].__name__ for x in self.game._walkthrough], ['description', 'location', 'interact', 'interact'])

        self.game._walkthrough_index = 0 #our location in the walkthrough
        self.game._walkthrough_target = 4  #our target

        self.game.update(0, single_event=True) #do the description step
        self.assertEqual(len(self.game._events), 0) #no events, so walkthrough could keep going

        self.game.update(0, single_event=True) #do the location test
        self.game.update(0, single_event=True) #do the interact that triggers the on_asks

        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_asks'])

        self.game.update(0, single_event=True) #do the interact that triggers the Hello World option
        self.game.update(0, single_event=True) #trigger the on_says
        self.game.update(0, single_event=True) #clear the on_says

        self.assertEqual([x[0].__name__ for x in self.game._events], [])
        

class CameraEventTest(unittest.TestCase):
    def setUp(self):
        self.game = Game("Unit Tests", fps=60, afps=16, resolution=RESOLUTION)
        self.game.settings = Settings()
        self.actor = Actor("_test_actor").smart(self.game)
        self.msgbox = Item("msgbox").smart(self.game, using="data/items/_test_item")
        self.ok = Item("ok").smart(self.game, using="data/items/_test_item")
        self.scene = Scene("_test_scene")
        self.game._headless = True
        self.game.add([self.scene, self.actor, self.msgbox, self.ok])

    def test_events(self):
        self.actor.says("Hello World", ok=False)
        self.game.camera.scene(self.scene)
        self.actor.says("Goodbye World", ok=False)

        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_says', "on_scene", "on_says"])
        self.game.update(0, single_event=True) #do the says step
        self.game.update(0, single_event=True) #remove the says step

        self.assertEqual([x[0].__name__ for x in self.game._events], ["on_scene", "on_says"])

        self.game.update(0, single_event=True) #do the camera step

        self.assertEqual([x[0].__name__ for x in self.game._events], ["on_says"])


class GotoTest(unittest.TestCase):
    def setUp(self):
        self.game = Game("Unit Tests", fps=60, afps=16, resolution=RESOLUTION)
        self.game.settings = Settings()
        self.actor = Actor("_test_actor").smart(self.game)
        self.msgbox = Item("msgbox").smart(self.game, using="data/items/_test_item")
        self.ok = Item("ok").smart(self.game, using="data/items/_test_item")
        self.scene = Scene("_test_scene")
        self.game._headless = False
        self.game.add([self.scene, self.actor, self.msgbox, self.ok])
        self.scene._add(self.actor)
        self.game.camera._scene(self.scene)

    def goto(self):
        self.actor.x, self.actor.y = 100,100
        self.actor._calculate_goto((200,100)) #left
        self.actor._calculate_goto((100,200)) #down
        self.actor._calculate_goto((0,100)) #right
        self.actor._calculate_goto((100, 0)) #up
        self.actor._calculate_goto((0,92))
#        self.actor._calculate_goto(self, (200,100))

    def test_goto(self):
        dt = 0
        speed = 10
        for i in self.actor._actions.values(): i.speed = speed
        self.actor.x, self.actor.y = 100,100
        self.actor.goto((200,100))
        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_goto'])
        self.game.update(0, single_event=True) #do the goto event

        #should be walking to the right at angle 90, speed 5
        self.assertEqual(self.actor.action.name, "right")
        self.assertEqual(self.actor._goto_x, 200)
        self.assertEqual(self.actor._goto_y, 100)
        self.assertEqual(self.actor._goto_dx, speed)
        self.assertEqual(self.actor._goto_dy, 0)

        #walk until we arrive
        for i in range(0,100//speed):
            self.game.update(0, single_event=True)
            self.assertEqual(self.actor.x, 100+speed+i*speed)
            self.assertEqual(self.actor.y, 100)
        self.assertEqual(self.actor._goto_x, None)
        self.assertEqual(self.actor._goto_y, None)
        self.assertAlmostEqual(self.actor._goto_dx, 0)
        self.assertAlmostEqual(self.actor._goto_dy, 0)

        
        # walk down
        self.actor.move((0,100))
        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_move'])
        self.game.update(0, single_event=True) #do the goto event
        self.assertEqual(self.actor.action.name, "down")
        self.assertEqual(self.actor._goto_x, 200)
        self.assertEqual(self.actor._goto_y, 200)
        self.assertAlmostEqual(self.actor._goto_dx, 0)
        self.assertEqual(self.actor._goto_dy, speed)
        for i in range(0,100//speed):
            self.game.update(0, single_event=True)
            self.assertEqual(self.actor.y, 100+speed+i*speed)
        self.game.update(0, single_event=True)
        self.assertEqual(self.actor._goto_x, None)
        self.assertEqual(self.actor.x, 200)
        self.assertEqual(self.actor.y, 200)


        # walk left and up, using "left"
        self.actor.move((-100, -8)) #(100, 192)
        self.assertEqual([x[0].__name__ for x in self.game._events], ['on_move'])
        self.game.update(0, single_event=True) #do the goto event
        self.assertEqual(self.actor.action.name, "left")
        self.assertEqual(self.actor._goto_x, 100)
        self.assertEqual(self.actor._goto_y, 192)

        self.assertTrue(9 > self.actor._goto_dx < 10) #slight under 10
        self.assertTrue(-1 < self.actor._goto_dy < 0) #slightly under -1
        for i in range(0,9): #takes 10 loops but  
            self.game.update(0, single_event=True)
            self.assertAlmostEqual(self.actor.y, 200+(i+1)*self.actor._goto_dy)
        self.game.update(0, single_event=True) #arrive
        self.assertEqual(self.actor._goto_x, None)


        #walk up and right, using "up"
        self.actor.move((20, -100)) #(120, 92)
        self.game.update(0, single_event=True) #do the goto event
        self.assertAlmostEqual(self.actor._goto_dx, 1.9611613513818404)
        self.assertAlmostEqual(self.actor._goto_dy,-9.80580675690920)
        self.assertEqual(self.actor.action.name, "up")


    def test_goto_queue(self):
        """ Test event queue """
        self.actor.x, self.actor.y = 100,100
        self.actor.says("Hello World")
        self.actor.goto(200,100)
        self.actor.says("Goodbye World")

class PortalTest(unittest.TestCase):
    def setUp(self):
        self.game = Game("Unit Tests", fps=60, afps=16, resolution=RESOLUTION)
        self.game.settings = Settings()
        self.actor = Actor("_test_actor").smart(self.game)
        speed = 10
        for i in self.actor._actions.values(): i.speed = speed

        self.scene = Scene("_test_scene")
        self.scene2 = Scene("_test_scene2")
        self.portal1 = Portal("_test_portal1")
        self.portal2 = Portal("_test_portal2")
        self.portal1.link = self.portal2
        self.portal2.link = self.portal1

        self.portal1.x, self.portal1.y = 100,0
        self.portal1.sx, self.portal1.sy = 0,0
        self.portal1.ox, self.portal1.oy = 100,0

        self.portal2.x, self.portal2.y = 1100,0
        self.portal1.sx, self.portal1.sy = 0,0
        self.portal1.ox, self.portal1.oy = -100,0

        self.game._headless = False
        self.game.player = self.actor
        self.game.add([self.scene, self.actor, self.portal1, self.portal2])
        self.scene._add([self.actor, self.portal1])
        self.scene2._add([self.portal2])
        self.game.camera._scene(self.scene)

    def test_events(self):
        portal = self.portal1
        game = self.game

        #queue the events
        portal.exit_here() 
        game.camera.scene("aqueue", RIGHT)
        game.camera.pan(left=True)
        portal.relocate_link() #move player to new scene
        portal.enter_link() #enter scene
        self.assertEqual([x[0].__name__ for x in self.game._events],['on_goto', 'on_goto', 'on_scene', 'on_pan', 'on_relocate', 'on_goto'])
        for i in range(0,11): #finish first goto
            self.game.update(0, single_event=True)
#            self.assertAlmostEqual(self.actor.y, 200+(i+1)*self.actor._goto_dy)
        import pdb; pdb.set_trace()
        self.assertEqual([x[0].__name__ for x in self.game._events],['on_goto', 'on_scene', 'on_pan', 'on_relocate', 'on_goto'])

if __name__ == '__main__':
    unittest.main()
