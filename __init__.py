"""
Python3 
"""
import glob, imp, json, pyglet, os, sys, copy
from datetime import datetime
import tkinter as tk
import tkinter.filedialog

import threading, traceback
from random import choice

from argparse import ArgumentParser
from collections import Iterable
from gettext import gettext

from pyglet.image.codecs.png import PNGImageDecoder

try:
    import android
except ImportError:
    android = None

try:
    import logging
    import logging.handlers
except ImportError:
    logging = None


"""
Constants
"""
DEBUG_ASTAR = False
DEBUG_STDOUT = True #stream errors to stdout as well as log file

ENABLE_EDITOR = True #default for editor
ENABLE_PROFILING = False
ENABLE_LOGGING = True
ENABLE_LOCAL_LOGGING = True
DEFAULT_TEXT_EDITOR = "gedit"

VERSION_MAJOR = 5 #major incompatibilities
VERSION_MINOR = 0 #minor/bug fixes, can run same scripts
VERSION_SAVE = 5  #save/load version, only change on incompatible changes

#AVAILABLE BACKENDS
PYGAME19 = 0
PYGAME19GL = 1
PYGLET12 = 2
BACKEND = PYGAME19

COORDINATE_MODIFIER = -1 #pyglet has (0,0) in bottom left, we want it in the bottom right

HIDE_MOUSE = True #start with mouse hidden, first splash will turn it back on
DEFAULT_FULLSCREEN = False #switch game to fullscreen or not
DEFAULT_EXPLORATION = True #show "unknown" on portal links before first visit there
DEFAULT_PORTAL_TEXT = True #show portal text


DEFAULT_RESOLUTION = (1920, 1080)
DEFAULT_FPS = 60
DEFAULT_ACTOR_FPS = 16

DIRECTORY_ACTORS = "data/actors"
DIRECTORY_PORTALS = "data/portals"
DIRECTORY_ITEMS = "data/items"
DIRECTORY_SCENES = "data/scenes"
DIRECTORY_FONTS = "data/fonts"
DIRECTORY_EMITTERS = "data/emitters"
DIRECTORY_SAVES = "saves"
DIRECTORY_INTERFACE = "data/interface"

DEFAULT_MENU_FONT = os.path.join(DIRECTORY_FONTS, "vera.ttf")
DEFAULT_MENU_SIZE = 26
DEFAULT_MENU_COLOUR = (42, 127, 255)



#LAYOUTS FOR MENUS and MENU FACTORIES
HORIZONTAL = 0
VERTICAL = 1    

#on says position
POSITION_BOTTOM = 0
POSITION_TOP = 1
POSITION_LOW = 2
POSITION_TEXT = 3 #play at text point of actor


#ANCHORS FOR MENUS and MENU FACTORIES
LEFT = 0
RIGHT = 1
CENTER = 2

MOUSE_USE = 1
MOUSE_LOOK = 2  #SUBALTERN
MOUSE_INTERACT = 3   #DEFAULT ACTION FOR MAIN BTN


#WALKTHROUGH EXTRAS KEYWORDS
LABEL = "label"
HINT = "hint"


#EDITOR CONSTANTS
MENU_EDITOR = "e_load", "e_save", "e_add", "e_delete", "e_prev", "e_next", "e_walk", "e_portal", "e_scene", "e_step", "e_reload", "e_jump", "e_state_save", "e_state_load"

#KEYS
K_ESCAPE = "X"
K_s = "s"

"""
GLOBALS (yuck)
"""
_pyglet_fonts = {DEFAULT_MENU_FONT:"Vera"}


"""
Testing utilities
"""

#### pygame testing functions ####

def reset(): pass #stub for letting save game know when a reset point has been reached

def goto(): pass #stub

def interact(): pass #stub

def use(): pass #stub

def look(): pass #stub

def has(): pass #stub

def select(): pass #stub

def toggle(): pass #stub 

def assertLocation(): pass #stub

def assertVicinty(): pass #stub

def location(): pass #stub #XXX deprecated

def description(): pass #used by walkthrough output

"""
Logging
"""

def create_log(logname, fname, log_level):
    log = logging.getLogger(logname)
    if logging: log.setLevel(log_level)

    handler = logging.handlers.RotatingFileHandler(fname, maxBytes=2000000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    log.addHandler(handler)
    if DEBUG_STDOUT:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setLevel(logging.ERROR)
        log.addHandler(handler)
    return log


if logging:
    if ENABLE_LOGGING:
        log_level = logging.DEBUG #what level of debugging
    else:
        log_level = logging.WARNING
    LOG_FILENAME = os.path.join(DIRECTORY_SAVES, 'pyvida.log')
    ANALYSIS_FILENAME = os.path.join(DIRECTORY_SAVES, 'analysis.log')
    log = create_log("pyvida", LOG_FILENAME, log_level)
    analysis_log = create_log("analysis", ANALYSIS_FILENAME, log_level)


"""
Utilities
"""
def deslugify(txt):
    """ replace underscores with spaces, basically """
    return txt.replace("_", " ")

def slugify(txt):
    """ slugify a piece of text """
    txt = txt.replace(" ", "_")
    txt = txt.replace("-", "")
    txt = txt.replace(".", "_")
    txt = txt.replace("!", "")
    txt = txt.replace("+", "")
    txt = txt.replace("]", "")
    txt = txt.replace("[", "")
    txt = txt.replace("}", "")
    txt = txt.replace("{", "")
    txt = txt.replace("/", "_")
    txt = txt.replace("\\", "_")
    return txt.replace("'", "")

def get_available_languages():
    """ Return a list of available locale names """
    languages = glob.glob("data/locale/*")
    languages = [os.path.basename(x) for x in languages if os.path.isdir(x)]
    languages.sort()
    if language not in languages:
        languages.append(language) #the default
    return languages
  
def load_image(fname, convert_alpha=False, eight_bit=False):
    with open(fname, "rb") as f:
        im = pyglet.image.codecs.pil.PILImageDecoder().decode(f, fname)
#    im = pyglet.image.codecs.png.PNGImageDecoder().decode(open(fname, "rb"), fname)
#    im = pyglet.image.load(fname)
#    im = pyglet.image.load(fname, decoder=PNGImageDecoder())
    return im

def get_font(game, filename, fontname):
    pyglet.font.add_file(filename)
    return pyglet.font.load(fontname)


def get_point(game, destination):
    """ get a point from a tuple, str or destination """
    if type(destination) in [str]:
        if destination in game._actors: destination = (game._actors[destination].sx, game._actors[destination].sy)
        elif destination in game._items: destination = (game._items[destination].sx, game._items[destination].sy)
        
    elif type(destination) == object:
        destination = (destination.sx, destination.sy)
    return destination

def get_object(game, obj):
    """ get an object from a name or object """
    if type(obj) != str: return obj
    robj = None #return object
    if obj in game._scenes: 
        robj = game._scenes[obj]
    elif obj in game._items.keys(): 
        robj = game._items[obj]
    elif obj in game._actors.keys(): 
        robj = game._actors[obj]
    else: #look for the display names in _items in case obj is the name of an on_ask option
        for i in game._items.values():
            if obj == i.display_text: robj = i
    return robj


def collide(rect, x,y):
    """ text is point x,y is inside rectangle """
    return not ((x < rect[0])
        or (x > rect[2] + rect[0])
        or (y < rect[1])
        or (y > rect[3] + rect[1]))


class answer(object):
    """
    A decorator for functions that you wish to use as options in an Actor.on_ask event

    Keyword arguments:
    opt -- the text to display in the question
    """
    def __init__(self, opt):
        self.opt = opt
    def __call__(self, answer_callback):
        return (self.opt, answer_callback)


def get_smart_directory(game, obj):
    """
    Given an pyvida object, return the smartest parent directory for it.
    """
#    if isinstance(obj, Emitter):
#        d = game.emitter_dir
    if isinstance(obj, Portal):
        d = game.directory_portals
    elif isinstance(obj, Emitter):
        d = game.directory_emitters
    elif isinstance(obj, Item):
        d = game.directory_items
    elif isinstance(obj, Actor):
        d = game.directory_actors
    elif isinstance(obj, Scene):
        d = game.directory_scenes
    return d

def get_function(game, basic):
    """ 
        Search memory for a function that matches this name 
        Also search any modules in game._modules (eg used when cProfile has taken control of __main__ )
    """
    if hasattr(basic, "__call__"): basic = basic.__name__
    script = None
    module = "main" if android else "__main__" #which module to search for functions
    extra_modules = game._modules if __name__ == "pyvida" and game else []
    modules = [module]
    modules.extend(extra_modules.keys())
    for m in modules:
        if m not in sys.modules: continue
        if hasattr(sys.modules[m], basic):
              script = getattr(sys.modules[m], basic)
              break
        elif hasattr(sys.modules[m], basic.lower()):
              script = getattr(sys.modules[m], basic.lower())
              break
    return script


def create_event(q):
    return lambda self, *args, **kwargs: self.game.queue_event(q, self, *args, **kwargs)

def use_on_events(name, bases, dic):
    """ create a small method for each "on_<x>" queue function """
    for queue_method in [x for x in dic.keys() if x[:3] == 'on_']:
        qname = queue_method[3:]
#        if logging: log.debug("class %s has queue function %s available"%(name.lower(), qname))
        dic[qname] = create_event(dic[queue_method])
    return type(name, bases, dic)


"""
Classes
"""


#If we use text reveal
SLOW = 0
NORMAL = 1
FAST = 2
class Settings(object):
    """ game settings saveable by user """
    def __init__(self):
        self.music_on = True
        self.sfx_on = True
        self.voices_on = True
        
#        self.music_volume = 0.6
        self.music_volume = 0.6 #XXX music disabled by default
        self.sfx_volume = 0.8
        self.sfx_subtitles = False
        self.voices_volume = 0.8
        self.voices_subtitles = True
        
        self.resolution_x = 1024
        self.resolution_y = 768
        
        self.allow_internet = None #True|False|None check for updates and report stats - None == False and user hasn't been asked
        self.allow_internet_debug = ENABLE_LOGGING #send profiling reports home
        
        self.fullscreen = DEFAULT_FULLSCREEN
        self.show_portals = False
        self.show_portal_text = DEFAULT_PORTAL_TEXT
        self.portal_exploration = DEFAULT_EXPLORATION
        self.textspeed = NORMAL
        self.fps = DEFAULT_FPS
        self.stereoscopic = False #display game in stereoscopic (3D)
        self.hardware_accelerate = False 
        self.backend = BACKEND
        
        self.high_contrast = False
        self.accessibility_font = None #use this font to override main font (good for using dsylexic-friendly fonts
                
        self.invert_mouse = False #for lefties
        self.language = "en"




    def save(self, save_dir):
        """ save the current game settings """
        if logging: log.debug("Saving settings to %s"%save_dir)
        fname = os.path.join(save_dir, "game.settings")
        with open(fname, "w") as f:
           pickle.dump(self, f)

    def load(self, save_dir):
        """ load the current game settings """
        if logging: log.debug("Loading settings from %s"%save_dir)
        fname = os.path.join(save_dir, "game.settings")
        try:
            with open(fname, "rU") as f:
               data = pickle.load(f)
            return data
        except: #if any problems, use default settings
            log.warning("Unable to load settings from %s, using defaults"%fname)
            #use loaded settings            
            return self 



class Action(object):
    def __init__(self, name):
        self.name = name
        self.actor = None
        self.game = None
        self._sprite = None

    def draw(self):
        self._sprite.draw()

    def smart(self, game, actor=None, filename=None): #action.smart
        #load the image and slice info if necessary
        self.actor = actor if actor else self.actor
        self.game = game
        image = load_image(filename)
        fname = os.path.splitext(filename)[0]
        montage_fname = fname + ".montage"
        if not os.path.isfile(montage_fname):
            num, w,h = 1, 0, 0
        else:
            with open(montage_fname, "r") as f:
                try:
                    num, w, h  = [int(i) for i in f.readlines()]
                except ValueError as err:
                    if logging: log.error("Can't read values in %s (%s)"%(self.name, montage_fname))
                    num,w,h = 0,0,0

        image_seq = pyglet.image.ImageGrid(image, 1, num)
        frames = []
        for frame in image_seq: #TODO: generate ping poing, reverse effects here
            frames.append(pyglet.image.AnimationFrame(frame, 1/game.default_actor_fps))
        self._animation = pyglet.image.Animation(frames)
        return self

    
class Rect(object):
    def __init__(self, x,y,w,h):
        self.x, self.y = x, y
        self.w, self.h = w, h

    def __str__(self):
        return "{}, {}, {}, {}".format(self.x, self.y, self.w, self.h)

    def collidepoint(self, x, y):
        return collide((self.x, self.y, self.w, self.h), x,y)

    def move(self, dx, dy):
        return Rect(self.x+dx, self.y+dy, self.w, self.h)

    @property
    def center(self):
        return (self.x + self.w//2, self.y + self.h//2)



def crosshair(game, point, colour):

        fcolour = fColour(colour)
        pyglet.gl.glColor4f(*fcolour)       

        #y is inverted for pyglet
        x,y=point[0], game.resolution[1]-point[1]                               
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ('v2i', (x, y-5, x, y+5))) 
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ('v2i', (x-5, y, x+5, y))) 
        pyglet.gl.glColor4f(1.0, 1.0, 1.0, 1.0) # undo alpha for pyglet drawing

        label = pyglet.text.Label("{0}, {1}".format(x,y),
                          font_name='Arial',
                          font_size=10,
                          color=colour,
                          x=x+6, y=y,
                          anchor_x='left', anchor_y='center')
        label.draw()
        return point


def rectangle(game, rect, colour=(255, 255, 255, 255)):
        fcolour = fColour(colour)
        pyglet.gl.glColor4f(*fcolour)               
        x,y=rect.x,rect.y
        w,h=rect.w,rect.h

        #y is inverted for pyglet
        gy = game.resolution[1]-y
        p1 = (x, gy)
        p2 = (x + w, gy)
        p3 = (x + w, gy - h)
        p4 = (x, gy - h)
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ('v2i', (p1[0], p1[1], p2[0], p2[1]))) 
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ('v2i', (p2[0],p2[1], p3[0], p3[1]))) 
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ('v2i', (p3[0],p3[1], p4[0], p4[1]))) 
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES, ('v2i', (p4[0],p4[1], p1[0], p1[1]))) 
        pyglet.gl.glColor4f(1.0, 1.0, 1.0, 1.0) # undo alpha for pyglet drawing

        label = pyglet.text.Label("{0}, {1}".format(x,game.resolution[1]-y),
                          font_name='Arial',
                          font_size=10,
                          color=colour,
                          x=x+w+6, y=gy-h,
                          anchor_x='left', anchor_y='top')
        label.draw()
        return [p1, p2, p3, p4]

def fColour(colour):
    """ Convert a pyglet colour (0-255) to a floating point (0 - 1.0) colour as used by GL  """
    return map(lambda x: x/255, colour)


def get_pixel_from_image(image, x, y):
        #Grab 1x1-pixel image. Converting entire image to ImageData takes much longer than just
        #grabbing the single pixel with get_region() and converting just that.
        image_data = image.get_region(int(x),int(y),1,1).get_image_data()
        #Get (very small) image as a string. The magic number '4' is just len('RGBA').
        data = image_data.get_data('RGBA',4)
        #Convert Unicode strings to integers. Provided by Alex Holkner on the mailing list.
        #components = map(ord, list(data))        #components only contains one pixel. I want to return a color that I can pass to
        #pyglet.gl.glColor4f(), so I need to put it in the 0.0-1.0 range.
        try:
            return (data[0], data[1], data[2], data[3])
        except:
            import pdb; pdb.set_trace()



#signal dispatching, based on django.dispatch
class Signal(object):
    def __init__(self, providing_args=None):
        self.receivers = []
        if providing_args is None:
            providing_args = []
        self.providing_args = set(providing_args)
       
    def connect(self, receiver, sender):
        if (receiver, sender) not in self.receivers: self.receivers.append((receiver, sender))


post_interact = Signal(providing_args=["game", "instance", "player"])
pre_interact = Signal(providing_args=["game", "instance", "player"])

post_use = Signal(providing_args=["game", "instance", "player"])
pre_use = Signal(providing_args=["game", "instance", "player"])

pre_leave = Signal(providing_args=["game", "instance", "player"])
post_arrive = Signal(providing_args=["game", "instance", "player"])

def receiver(signal, **kwargs):
    """
    A decorator for connecting receivers to signals. Used by passing in the
    signal and keyword arguments to connect::

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs):
            ...

    """
    def _decorator(func):
        signal.connect(func, **kwargs)
        return func
    return _decorator


"""
Classes
"""

class Actor(metaclass=use_on_events):
    def __init__(self, name, interact=None):
        super().__init__()
        self.name = name
        self._actions = {}
        self.action = None
        self.game = None
        self.scene = None
        self._x, self._y = 0, 0
        self._sx, self._sy = 0, 0 #stand points
        self._ax, self._ay = 0, 0 #anchor points
        self._nx, self._ny = 0, 0 # displacement point for name
        self._tx, self._tx = 0, 0 # displacement point for text
        self._parent = None

        self.z = 1000 #where in the z layer is this actor (< 1000 further away, >1000 closer to player)
        self.scale = 1.0
        self.rotate = 0

        self.display_text = None #can override name for game.info display text
        self.display_text_align = LEFT
        self.font_speech = None #use default font (from game)
        self.font_speech_size = None #use default font size (from game)
        self.font_colour = None #use default

        self._solid_area = Rect(0,0,60,100)
        self._clickable_area = Rect(0, 0, 0, 0)
        self._clickable_mask = None
        self._clickable_fullscreen = False #override clickable to make it cover all the screen

        self._allow_draw = True
        self.allow_update = True
        self.allow_use = True
        self.allow_interact = True
        self.allow_look = True
        self._editing = None #what attribute of this Actor are we editing
        self._editing_save = True #allow saving via the editor
        self.show_debug = False 

        self._interact = interact #special queuing function for interacts
        self.look = None #override queuing function for look
        self.uses = {} #override use functions (actor is key name)
        self.facts = []
        self.inventory = {}

        self._directory = None
        self._busy = False
        self._sprite = None
        self._events = []

        self._tint = None
        self._editable = [ #(human readable, get variable names, set variable names, widget types)
            ("position", (self.get_x, self.get_y), (self.set_x, self.set_y),  (int, int)),
            ("anchor", (self.get_ax, self.get_ay), (self.set_ax, self.set_ay), (int, int)),
            ("interact", self.get_interact, self.set_interact, str),
            ("allow_draw", self.get_allow_draw, self.set_allow_draw, bool), # ( "allow_update", "allow_use", "allow_interact", "allow_look"]        
            ]

    def get_busy(self, x):
        return self._busy
    def set_busy(self, x):
        print("Set %s busy to %s"%(self.name, x))
        self._busy = x
    busy = property(get_busy, set_busy)


    def update_anchor(self):
        if isinstance(self._sprite._animation, pyglet.image.Animation):
            for f in _sprite._animation:
                f.image.anchor_x = self._ax
                f.image.anchor_y = self._ay
        else:
            self._sprite._animation.anchor_x = self._ax
            self._sprite._animation.anchor_y = self._ay

    def get_x(self): return self._x
    def set_x(self, v): self._x = v
    x = property(get_x, set_x)

    def get_y(self): return self._y
    def set_y(self, v): self._y = v
    y = property(get_y, set_y)

    def get_ax(self):
        return self._ax
    def set_ax(self, v):
        self._ax = v
        if self._sprite: self._sprite.anchor_x = v  - self.x
        return
    ax = property(get_ax, set_ax)

    def get_ay(self):
        return self._ay
    def set_ay(self, v):
        self._ay = v 
        if self._sprite: self._sprite.anchor_y = v - self.y
        return
    ay = property(get_ay, set_ay)

    def get_tx(self): return self._tx
    def set_tx(self, v): self._tx = v
    tx = property(get_tx, set_tx)
    def get_ty(self): return self._ty
    def set_ty(self, v): self._ty = v
    ty = property(get_ty, set_ty)

    def get_nx(self): return self._nx
    def set_nx(self, v): self._nx = v
    nx = property(get_nx, set_nx)
    def get_ny(self): return self._ny
    def set_ny(self, v): self._ny = v
    ny = property(get_ny, set_ny)

    def get_sx(self): return self._sx
    def set_sx(self, v): self._sx = v
    sx = property(get_sx, set_sx)
    def get_sy(self): return self._sy
    def set_sy(self, v): self._sy = v
    sy = property(get_sy, set_sy)

    def set_interact(self, v):
        self._interact = v
    def get_interact(self):
        return self._interact
    interact = property(get_interact, set_interact)

    def set_allow_draw(self, v):
        self._allow_draw = v
    def get_allow_draw(self):
        return self._allow_draw
    allow_draw = property(get_allow_draw, set_allow_draw)

    @property
    def w(self):
        return self._sprite.width

    @property
    def h(self):
        return self._sprite.height

    def _get_text_details(self, font=None, size=None, wrap=None):
        """ get a dict of details about the speech of this object """
        kwargs = {}
        if wrap != None: kwargs["wrap"] = wrap
        if self.font_colour != None: kwargs["colour"] = self.font_colour
        if font:
            kwargs["font"] = font 
        elif self.font_speech:
            kwargs["font"] = self.font_speech
        elif self.game and self.game.font_speech:
            kwargs["font"] = self.game.font_speech
        if size:
            kwargs["size"] = size
        elif self.font_speech_size:
            kwargs["size"] = self.font_speech_size
        elif self.game and self.game.font_speech_size:
            kwargs["size"] = self.game.font_speech_size
        return kwargs


    def _update(self, dt):
        pass

    @property
    def clickable_area(self):
        return self._clickable_area.move(self.x + self.ax, self.y + self.ay)

    @property
    def clickable_mask(self):
        if self._clickable_mask: return self._clickable_mask
#        r = self._clickable_area.move(self.ax, self.ay)
#        if self.scale != 1.0:
#            r.width *= self.scale
#            r.height *= self.scale
        mask = pyglet.image.SolidColorImagePattern((255, 255, 255, 255))
        self._clickable_mask = mask.create_image(self.clickable_area.w, self.clickable_area.h)
        return self._clickable_mask

    def fullscreen(self, v=True): #make the clickable_area cover the whole screen, useful for some modals
        self._clickable_fullscreen = v

    def collide(self, x,y, image=False): #Actor.collide
        """ collide with actor's clickable 
            if image is true, ignore clickable and collide with image.
        """
        if self._clickable_fullscreen: return True
        if not self.clickable_area.collidepoint(x,y): return
#        x = x - self.x 
#        y = y - self.y - self.clickable_area.y
#        if self.name == "New Game": import pdb; pdb.set_trace()
        data = get_pixel_from_image(self.clickable_mask, x - self.clickable_area.x, y - self.clickable_area.y)
        if data[:2] == (0,0,0) or data[3] == 255: return False #clicked on black or transparent, so not a collide
        return True
#        else:
#            return collide(self._image().get_rect().move(self.x, self.y), x, y)


    def trigger_interact(self):
        print("Interact with",self.name)
        if self.interact: #if user has supplied an interact override
            if type(self.interact) in [str]: 
                interact = get_function(self.game, self.interact)
                if interact: 
                    self.interact = interact
                else:
                    if logging: log.error("Unable to find interact fn %s"%self.interact)
            n = self.interact.__name__ if self.interact else "self.interact is None"
            if logging: log.debug("Player interact (%s (%s)) with %s"%(n, self.interact if self.interact else "none", self.name))
            script = self.interact
            script(self.game, self, self.game.player)
        else: #else, search several namespaces or use a default
            basic = "interact_%s"%slugify(self.name)
            script = get_function(self.game, basic)
            if script:
#                if self.game.edit_scripts: 
#                    edit_script(self.game, self, basic, script, mode="interact")
#                    return
    
                if not self.game._catch_exceptions: #allow exceptions to crash engine
                    script(self.game, self, self.game.player)
                else:
                    try:
                        script(self.game, self, self.game.player)
                    except:
                        log.error("Exception in %s"%script.__name__)
                        print("\nError running %s\n"%script.__name__)
                        if traceback: traceback.print_exc(file=sys.stdout)
                        print("\n\n")
                        
                if logging: log.debug("Player interact (%s) with %s"%(script.__name__, self.name))
            else:
                #warn if using default vida interact
                if not isinstance(self, Portal):
                    if logging: log.warning("No interact script for %s (write a def %s(game, %s, player): function)"%(self.name, basic, slugify(self.name)))
                script = None #self._interact_default
                self._interact_default(self.game, self, self.game.player)

        for receiver, sender in post_interact.receivers: #do the signals for post_interact
            if isinstance(self, sender): 
                receiver(self.game, self, self.game.player)


    def _interact_default(self, game, actor, player):
        """ default queuing interact smethod """
        if isinstance(self, Item): #very generic
            c = ["It's not very interesting.",
            "I'm not sure what you want me to do with that.",
            "I've already tried using that, it just won't fit."]
        else: #probably an Actor object
            c = ["They're not responding to my hails.",
            "Perhaps they need a good poking.",
            "They don't want to talk to me."]
        if self.game.player: self.game.player.says(choice(c))




    def smart(self, game, image=None, using=None, idle="idle", action_prefix = ""): #actor.smart
        """ 
        Intelligently load as many animations and details about this actor/item.
        
        Most of the information is derived from the file structure.
        
        If no <image>, smart will load all .PNG files in data/actors/<Actor Name> as actions available for this actor.

        If there is an <image>, create an idle action for that.
        
        If <using>, use that directory to smart load into a new object with <name>

        If <idle>, use that action for defaults rather than "idle"

        If <action_prefix>, prefix value to defaults (eg astar, idle), useful for swapping clothes on actor, etc 
        """
        DEFAULT_CLICKABLE = Rect(0, 0, 70, 110)
        self.game = game
        if using:
            if logging: log.info("actor.smart - using %s for smart load instead of real name %s"%(using, self.name))
            name = os.path.basename(using)
            d = os.path.dirname(using)
        else:
            name = self.name
            d = get_smart_directory(game, self)

        myd = os.path.join(d, name)        
        if not os.path.isdir(myd): #fallback to pyvida defaults
            this_dir, this_filename = os.path.split(__file__)
            log.debug("Unable to find %s, falling back to %s"%(myd, this_dir))
            myd = os.path.join(this_dir, d, name)

        self._directory = myd

        if image:
            images = [image]
        else:
            images = glob.glob(os.path.join(myd, "*.png"))
            if os.path.isdir(myd) and len(glob.glob("%s/*"%myd)) == 0:
                if logging: log.info("creating placeholder file in empty %s dir"%name)
                f = open(os.path.join(d, "%s/placeholder.txt"%name),"a")
                f.close()
        for action_file in images:
            action_name = os.path.splitext(os.path.basename(action_file))[0]
            action = Action(action_name).smart(game, actor=self, filename=action_file)
            self._actions[action_name] = action
        if len(self._actions)>0: #do an action by default
            self._do("idle" if "idle" in self._actions else list(self._actions.keys())[0])

        #guessestimate the clickable mask for this actor
        if self._sprite:
            w,h = self._sprite.width,self._sprite.height
            self._clickable_area = Rect(0, 0, w, h)
            if logging: log.debug("Setting %s _clickable area to %s"%(self.name, self._clickable_area))
        else:
            if not isinstance(self, Portal):
                if logging: log.warning("%s %s smart load unable to get clickable area from action image, using default"%(self.__class__, self.name))
            self._clickable_area = DEFAULT_CLICKABLE


        #potentially load some defaults for this actor
        filepath = os.path.join(myd, "%s.defaults"%slugify(self.name).lower())
        if os.path.isfile(filepath):
            actor_defaults = json.loads(open(filepath).read())
            for key, val in actor_defaults.items():
                if key == "font_colour": 
                    if type(val) == list:
                        val = tuple(val)
                    elif val in COLOURS: 
                        val = COLOURS[val]
                self.__dict__[key] = val
            

        #potentially load some interact/use/look scripts for this actor
        filepath = os.path.join(myd, "%s.py"%slugify(self.name).lower())
        if os.path.isfile(filepath):
            #add file directory to path so that import can find it
            if os.path.dirname(filepath) not in sys.path: sys.path.append(os.path.dirname(filepath))
            #add to the list of modules we are tracking
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            game._modules[module_name] = 0
            __import__(module_name) #load now
            game.reload_modules(modules=[module_name]) #reload now to refresh existing references

        return self

    def pyglet_draw(self): #actor.draw
        if self._sprite and self._allow_draw:
            self._sprite.position = (self.x + self.ax, self.game.resolution[1] - self.y - self.ay - self._sprite.height)
            self._sprite.draw()
        if self.show_debug:
            self.debug_pyglet_draw()

    def debug_pyglet_draw(self):
        """ Draw some debug info (store it for the unittests) """
        self._debugs = []
        #position = green
        self._debugs.append(crosshair(self.game, (self.x, self.y), (0, 255, 0, 255)))
        #anchor - blue
        self._debugs.append(crosshair(self.game, (self.x + self.ax, self.y + self.ay ), (0, 0, 255, 255)))
        #clickable area
        self._debugs.append(rectangle(self.game, self.clickable_area, (0, 255, 100, 255)))

    def on_animation_end(self):
#        self.busy = False
        frame = self._sprite._animation.frames[self._sprite._frame_index]

    def on_animation_end_once(self):
        """ When an animation has been called once only """
        self.busy = False
        self._do("idle")

    def on_asks(self, statement, *args, **kwargs):
        """ A queuing function. Display a speech bubble with text and several replies, and wait for player to pick one.

            Use the @answer decorator to avoid passing in tuples
            args are the options
            kwargs are passed through to on_says
        
        Examples::
        
            def friend_function(game, guard, player):
                guard.says("OK then. You may pass.")
                player.says("Thanks.")
                
            def foe_function(game, guard, player):
                guard.says("Then you shall not pass.")
                
            guard.asks("Friend or foe?", ("Friend", friend_function), ("Foe", foe_function), **kwargs)
        
        Options::
        
            tuples containing a text option to display and a function to call if the player selects this option.
            
        """    
        name = self.display_text if self.display_text else self.name
        if self.game._output_walkthrough: print("%s says \"%s\"."%(name, args[0]))
        items = self._says(statement, **kwargs) 
        label = None
        for item in items:
            if isinstance(item, Text): label=item
            def collide_never(x,y): #for asks, most modals can't be clicked, only the txt modelitam options can.
                return False
            item.collide = collide_never

        #add the options
        for i, option in enumerate(args):
            text, callback = option
            if self.game.player:
                kwargs =  self.game.player._get_text_details() #use the player's text options
            else:
                kwargs = self._get_text_details() #use the actor's text options
                kwargs["colour"] = (55, 255, 87) #but with a nice different colour
            #dim the colour of the option if we have already selected it.
            remember = (self.name, text, statement)
            if remember in self.game._selected_options and "colour" in kwargs:
                r,g,b= kwargs["colour"]
                kwargs["colour"] = (r/2, g/2, b/2)

            opt = Text("option{}".format(i), display_text=text, **kwargs)
            opt.x, opt.y = label.x + 10, label.y + (i+1)*opt.h + 5
            def answer_callback(game, btn, player):
                self._busy = False #no longer busy, so game can stop waiting
                self.game._modals = [] #empty modals
                print("ANSWER CALLBACK",i,btn.response_callback)
                btn.response_callback(game, btn, player)
            opt.interact = answer_callback
            opt.response_callback = callback
            self.game.add(opt)
            self.game._modals.append(opt)

    def on_says(self, text, *args, **kwargs):
        items = self._says(text, *args, **kwargs)
        if self.game._headless:  #headless mode skips sound and visuals
            items[0].trigger_interact() #auto-close the on_says


    def _says(self, text, action="portrait", font=None, size=None, using=None, position=None, delay=0.01, step=3, ok=True):
        #do high contrast if requested and available
        background = using if using else None
        high_contrast = "%s_high_contrast"%("msgbox" if not using else using)
        myd = os.path.join(self.game.directory_items, high_contrast)
        using = high_contrast if self.game.settings.high_contrast and os.path.isdir(myd) else background
        msgbox = get_object(self.game, "msgbox")
        if not msgbox:            
            msgbox = self.game.add(Item("msgbox").smart(self.game, using=using))
        if ok: ok = self.game.add(Item("ok").smart(self.game))

        kwargs =  self._get_text_details(font=font, size=size)
        if "wrap" not in kwargs:
            kwargs["wrap"] = msgbox.w*0.9
        label = Text(text, delay=delay, step=step, **kwargs)
        #position 10% off the bottom
        x, y = self.game.resolution[0]//2 - msgbox.w//2, self.game.resolution[1]*0.9 - msgbox.h

        label.game = self.game
        label.fullscreen(True)
        label.x,label.y = x+10,y+10
        if ok:
            try:
                ok.x, ok.y = x + msgbox.w - ok.w//2, y + msgbox.h - ok.h//2
            except:
                import pdb; pdb.set_trace()
        msgbox.x, msgbox.y = x,y

        #make the game wait until the user closes the modal
        self._busy = True 
        self.game._waiting = True

        items = [msgbox, label]
        if ok: items.append(ok)

        def close_on_says(game, obj, player):
            if ok: self.game._modals.remove(ok)
            self.game._modals.remove(label)
            self.game._modals.remove(msgbox)
            self._busy = False
        for obj in items:
            obj.interact = close_on_says
        self.game._modals.extend(items)
        return items

    def on_forget(self, fact):
        """ A queuing function. Forget a fact from the list of facts 
            
            Example::
            
                player.forget("spoken to everyone")
        """
        if fact in self.facts:
            self.facts.remove(fact)
            if logging: log.debug("Forgetting fact '%s' for player %s"%(fact, self.name))
        else:
            if logging: log.warning("Can't forget fact '%s' ... was not in memory."%(fact))
            
        #self._event_finish()

    def on_remember(self, fact):
        """ A queuing function. Remember a fact to the list of facts
            
            Example::
                player.remember("spoken to everyone")            
        """
        if fact not in self.facts: self.facts.append(fact)

    def remembers(self, fact):
        """ A pseudo-queuing function. Return true if fact in the list of facts 

            Example::
        
                if player.remembers("spoken to everyone"): player.says("I've spoken to everyone")
        
        """
        return True if fact in self.facts else False       
    

    def on_collection_select(self, collection, obj):
        """ Called when this object is selected in a collection """
        print("handling object selection")
        import pdb; pdb.set_trace()
        


    def _do(self, action, callback=None):
        callback = self.on_animation_end if callback == None else callback
        if self._sprite:
            self._sprite.delete()
        self.action = self._actions[action]
        self._sprite = pyglet.sprite.Sprite(self.action._animation)
        if self._tint: self._sprite.color = self._tint 
        self._sprite.on_animation_end = callback

    def on_do(self, action):
        self.busy = False
        self._do(action)
        
    def on_do_once(self, action):
        self._do(action, self.on_animation_end_once)
#        if follow: self.do(follow)
        self.busy = True

    def on_tint(self, rgb):
        self._tint = rgb
        print("Finished tint",rgb, datetime.now())
        if self._sprite: self._sprite.color = self._tint 

    def on_idle(self, seconds):
        """ delay processing the next event for this actor """
        self.busy = True
        def finish_idle(dt, start):
            print("Finished idling",dt, start, datetime.now())
            self.busy = False
        pyglet.clock.schedule_once(finish_idle, seconds, datetime.now())


    def _set(self, attrs, values):
        for a,v in zip(attrs, values):
            setattr(self, a, v)

    def on_reanchor(self, point):
        self._set(("ax", "ay"), point)

    def on_reclickable(self, rect):
        self._clickable_mask = None #clear the mask
        self._set(["_clickable_area"], [rect])

    def on_resolid(self, rect):
        self._set(["_solid_area"], [rect])

    def on_rescale(self, v):
        self._set(["scale"], [v])

    def on_restand(self, point):
        self._set(("sx", "sy"), point)

    def on_retalk(self, point):
        log.warning("retalk has been renamed rename")

    def on_respeech(self, point):
        log.warning("respeech has been renamed retext")
        self.on_retext(point)

    def on_retext(self, point):
        self._set(["tx", "ty"], point)

    def on_rename(self, point):
        self._set(["nx", "ny"], point)
        
    def on_hide(self, interactive=False):
        """ A queuing function: hide the actor, including from all click and hover events 
        
            Example::
            
            player.hide()
        """
        self._usage(draw=False, update=False)
        
    def on_show(self, interactive=True):
        """ A queuing function: show the actor, including from all click and hover events 
        
            Example::
            
                player.show()
        """
        self._usage(draw=True, update=True) # switch everything on


    def on_usage(self, draw=None, update=None, look=None, interact=None, use=None):
        """ Set the player->object interact flags on this object """

    def _usage(self, draw=None, update=None, look=None, interact=None, use=None):
        if draw != None: self._allow_draw = draw 
        if update != None: self.allow_update = update
        if look != None: self.allow_look = look
        if interact != None: self.allow_interact = interact
        if use != None: self.allow_use = use

    def _rescale(self, scale):
        self.scale = scale

    def on_relocate(self, scene, destination=None, scale=None): #actor.relocate
        self._relocate(scene, destination, scale)

    def _relocate(self, scene, destination=None, scale=None): #actor.relocate
        if scale: self._rescale(scale)
        scene = get_object(self.game, scene)
        scene._add(self)
        if destination:
            pt = get_point(self.game, destination)
            self.x, self.y = pt
        return

        if self.game and scene and self == self.game.player and self.game.test_inventory: #test player's inventory against scene        
            for inventory_item in self.inventory.values():
                for scene_item in scene.objects.values():
                    if type(scene_item) != Portal:
                        actee, actor = slugify(scene_item.name), slugify(inventory_item.name)
                        basic = "%s_use_%s"%(actee, actor)
                        fn = get_function(self.game, basic)
                        if not fn and inventory_item.name in scene_item.uses: fn = scene_item.uses[inventory_item.name]
                        if fn == None: #would use default if player tried this combo
                            if scene_item.allow_use: log.warning("%s default use script missing: def %s(game, %s, %s)"%(scene.name, basic, actee.lower(), actor.lower()))



class Item(Actor):
    pass

class Portal(Actor, metaclass=use_on_events):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ox, self._oy = 0,0 #out point for this portal

    def get_oy(self): return self._oy
    def set_oy(self, oy): self._oy = oy
    oy = property(get_oy, set_oy)

    def get_ox(self): return self._ox
    def set_ox(self, ox): self._ox = ox
    ox = property(get_ox, set_ox)   

    def on_auto_align(self): #auto align display_text
        if not self.game:
            log.warning("Unable to auto_align {} without a game object"%self.name)
            return
        if logging: log.warning("auto_align only works properly on 1024x768")
        if self.nx > self.game.resolution[0]//2: self.display_text_align = RIGHT #auto align text

    def on_reout(self, pt):
        """ queue event for changing the portal out points """
        self._ox, self._oy = pt[0], pt[1]



class Emitter(Item):
    def __init__(self, name, *args, **kwargs):
#    def __init__(self, name, number=10, frames=10, direction=0, fov=0, speed=1, acceleration=(0,0), size_start=1, size_end=1, alpha_start=1.0, alpha_end=0,random_index=0):
        super().__init__(name)

        log.warning("Emitters not implemented yet")


class WalkareaManager(object):
    """ Comptability layer with pyvida4 walkareas """
    def __init__(self, scene, game):
        self.scene = scene
        self.game = game
        log.warning("scene.walkareas is deprecated, please update your code")

    def set(self, *args, **kwargs):
        pass

class WalkArea(object):
    def __init__(self, *args, **kwargs):
        log.warning("WalkArea deprecated, please update your code")

    def smart(self, *args, **kwargs):
        return self



class Scene(metaclass=use_on_events):
    def __init__(self, name, game=None):
        self._objects = {}
        self.name = name
        self.game = game
        self._background = None
        self._background_fname = None
        self._foreground = []
        self._busy = False
        self._music_filename = None
        self._ambient_filename = None        

        self.x = 0
        self.y = 0
        self.display_text = None #used on portals if not None
        self.description = None #text for blind users
        self.scales = {}

        self.walkareas = WalkareaManager(self, game) #pyvida4 compatability


    @property
    def directory(self):
        return os.path.join(os.getcwd(),os.path.join(self.game.directory_scenes, self.name))    

    @property
    def background(self):
        if self._background: return self._background
        if self._background_fname:
            self._background = load_image(self._background_fname)
        return self._background

    def smart(self, game): #scene.smart
        self.game = game
        sdir = os.path.join(os.getcwd(),os.path.join(game.directory_scenes, self.name))
        bname = os.path.join(sdir, "background.png")
        self.game = game
        if os.path.isfile(bname):
            self.set_background(bname)
        self._load_foreground(game)

        # if there is an initial state, load that automatically
        state_name = os.path.join(sdir, "initial.py")
        if os.path.isfile(state_name): game.load_state(self, "initial")
        ambient_name = os.path.join(sdir, "ambient.ogg") #ambient sound to
        if os.path.isfile(ambient_name): self.ambient_fname = ambient_name

        #potentially load some defaults for this actor
        filepath = os.path.join(sdir, "%s.defaults"%slugify(self.name).lower())
        if os.path.isfile(filepath):
            object_defaults = json.loads(open(filepath).read())
            for key, val in object_defaults.items():
                self.__dict__[key] = val
        return self

    def _load_foreground(self, game):
        sdir = os.path.join(os.getcwd(),os.path.join(game.directory_scenes, self.name))    
        for element in glob.glob(os.path.join(sdir,"*.png")): #add foreground elments
            x,y = 0,0
            fname = os.path.splitext(os.path.basename(element))[0]

            if os.path.isfile(os.path.join(sdir, fname+".details")): #find a details file for each element
                with open(os.path.join(sdir, fname+".details"), "r") as f:
                    x, y  = [int(i) for i in f.readlines()]
#                a = Item(fname, x=x, y=y).createAction("idle", bname+fname)
                f = self.game._add(Item("%s_%s"%(self.name, fname)).smart(game, image=element))
                f.x, f.y = x,y
                self._foreground.append(f) #add foreground items as items


    def on_add(self, objects): #scene.add
        self._add(objects)

    def _add(self, objects): 
        if not isinstance(objects, Iterable): objects = [objects]
        for obj in objects:
            obj = get_object(self.game, obj)
            self._objects[obj.name] = obj
            obj.scene = self

    def _remove(self, obj):
        """ remove object from the scene """
        if type(obj) in [str]:
            if obj in self._objects:
                obj = self._objects[obj]
            else:
                if logging: log.warning("Object %s not in this scene %s"%(obj, self.name))
                return
        obj.scene = None
        if obj.name in self._objects:
            del self._objects[obj.name]
        else:
            log.warning("%s not in scene %s"%(obj.name, self.name))

    def on_remove(self, obj): #scene.remove
        """ queued function for removing object from the scene """
        if type(obj) == list:
            for i in obj: self._remove(i)
        else:
            self._remove(obj)
        

    def on_clean(self, objs=[]): #remove items not in this list from the scene
        for i in list(self._objects.values()):
            if i.name not in objs and not isinstance(i, Portal) and i != self.game.player: self._remove(i)


    def on_set_background(self, fname=None):
        self._set_background(fname)

    def _set_background(self, fname=None):
        if fname: log.debug("Set background for scene %s to %s"%(self.name, fname))
        if fname == None and self._background == None and self._background_fname: #load image
            fname = self._background_fname
        if fname:
            self._background_fname = fname

    def pyglet_draw(self): #scene.draw (not used)
        pass
#        if self._background:
#            print("Draw2!", len(self._objects), self._background)
#            self._background.blit(self.x, self.y)

        for obj in self._objects:
            print("drawing ",obj.name)
            obj.pyglet_draw()


class Text(Item):
    def __init__(self, name, pos=(0,0), display_text=None, colour=(255, 255, 255, 255), font=None, size=26, wrap=800, offset=0, interact=None, delay=0, step=2):
        """
        delay : How fast to display chunks of the text
        step : How many characters to advance during delayed display
        """
        self._label = None
        super().__init__(name, interact)

        self._display_text = display_text if display_text else name
        self.x, self.y = pos
        self.step = step

        #animate the text
        if delay>0:
            self._text_index = 0
            pyglet.clock.schedule_interval(self._animate_text, delay)
        else:
            self._text_index = len(self._display_text)

        self.__text = self._display_text[:self._text_index]

        if len(colour) == 3: colour = (colour[0], colour[1], colour[2], 255) #add an alpha value if needed
        font_name = "Times New Roman" #"Arial"
        if font:
            if font not in _pyglet_fonts:
                log.error("Unable to find %s in fonts, use game.add_font"%font)
            else:
                font_name = _pyglet_fonts[font]
        self._label = pyglet.text.Label(self.__text,
                                  font_name=font_name,
                                  font_size=size,
                                  color=colour,
                                  multiline=True,
                                  width=wrap,
                                  x=self.x, y=self.y,
                                  anchor_x='left', anchor_y='top')
        self._clickable_area = Rect(0, 0, self._label.content_width, self._label.content_height)
        
    def get_display_text(self):
        return self._display_text

    def set_display_text(self, v):
        self._display_text = v
        if self._label: self._label.text = v
    display_text = property(get_display_text, set_display_text)

    @property
    def w(self):
        return self._label.content_width

    @property
    def h(self):
        return self._label.content_height


    def _animate_text(self, dt):
        """ called by the clock at regular intervals """
        if self._text_index == len(self.display_text):
            pyglet.clock.unschedule(self._animate_text)
        else:
            self._text_index += self.step
            self.__text = self.display_text[:self._text_index]
            self._label.text = self.__text

    def pyglet_draw(self):
        if not self.game:
            log.warning("Unable to draw Text %s without a self.game object"%self.name)
            return
        x, y = self.x - self.ax, self.game.resolution[1] - self.y + self.ay 
        self._label.x, self._label.y = x,y
        self._label.draw()
        if self.show_debug:
            self.debug_pyglet_draw()


class Collection(Item, pyglet.event.EventDispatcher, metaclass=use_on_events):
    def __init__(self, name, callback, padding=(10,10), dimensions=(300,300), tile_size=50):
        super().__init__(name)
        self._objects = {}
        self._sorted_objects = None
        self.index = 0 #where in the index to start showing

        self.callback = callback
        self.padding = padding
        self.dimensions = dimensions
        self.tile_size = tile_size

    def on_empty(self):
        self._objects = {}
        self._sorted_objects = None
        self.index = 0


    def smart(self, *args, **kwargs):
        Item.smart(self, *args, **kwargs)
        self.dimensions = (self.clickable_area.w, self.clickable_area.h)
        return self

    def on_add(self, obj, callback=None):
        """ Add an object to this collection and set up an event handler for it in the event it gets selected """
        obj = get_object(self.game, obj)
#        obj.push_handlers(self) #TODO 
        self._objects[obj.name] = obj
        if callback:
            obj.on_collection_select = callback

    def something(self):
        obj = None #the object selected in the collection
        self.dispatch_events('on_collection_select', self, obj)

    def pyglet_draw(self): #collection.draw
        x,y = self.padding[0], self.padding[1]
        w = self.clickable_area.w
        for obj in self._objects.values():
            if obj._sprite:
                obj._sprite.position = (self.x + x, self.game.resolution[1] - self.y - y)
                obj._sprite.draw()
            if x + self.tile_size > self.dimensions[0]:
                x = self.padding[0]
            else:    
                x += self.tile_size + self.padding[0]
Collection.register_event_type('on_collection_select')

class MenuManager(metaclass=use_on_events):
    def __init__(self, game):
        super().__init__()
        self.name = "Default Menu Manager"
        self.game = game
        self._busy = False

    def on_show(self):
        for obj in self.game._menu: 
            obj.visible = True
        if logging: log.debug("show menu using place %s"%[x.name for x in self.game._menu])
        
    def _hide(self, menu_items = None):
        """ hide the menu (all or partial)"""
        if not menu_items:
            menu_items = self.game._menu
        if type(menu_items) not in [tuple, list]: menu_items = [menu_items]
        for i in menu_items:
            if type(i) in [str]: i = self.game.items[i]
            i.visible = False
        if logging: log.debug("hide menu using place %s"%[x.name for x in self.game._menu])

    def on_hide(self, menu_items = None):
        self._hide(self)

    def on_fade_out(self):
        log.warning("menumanager.fade_out does not fade")
        self._hide(self)

    def on_push(self):
        """ push this menu to the list of menus and clear the current menu """
        if logging: log.debug("push menu %s, %s"%([x.name for x in self.game._menu], self.game._menus))
#        if self.game._menu:
        self.game._menus.append(self.game._menu)
        self.game._menu = []

    def on_pop(self):
        """ pull a menu off the list of menus """
        if self.game._menus: self.game._menu = self.game._menus.pop()
        if logging: log.debug("pop menu %s"%[x.name for x in self.game._menu])


    def on_clear(self, menu_items = None):
        """ clear current menu """
        if not menu_items:
            self.game._menu = []
        else:
            if not hasattr(menu_items, '__iter__'): menu_items = [menu_items]
            for i in menu_items:
                obj = get_object(self.game, i)
                if obj in self.game._menu: self.game._menu.remove(obj)


class Camera(metaclass=use_on_events): #the view manager
    def __init__(self, game):
        self.name = "Default Camera"
        self.game = game
        self._busy = False
        self._ambient_sound = None
        

    def _scene(self, scene, camera_point=None):
        """ change the current scene """
        if self.game.scene: #unload background when not in use
            self.game.scene._background = None
        game = self.game
        if scene == None:
            if logging: log.error("Can't change to non-existent scene, staying on current scene")
            scene = self.game.scene
        if type(scene) in [str]:
            if scene in self.game._scenes:
                scene = self.game._scenes[scene]
            else:
                if logging: log.error("camera on_scene: unable to find scene %s"%scene)
                scene = self.game.scene
#        if self.game.text:
#            print("The view has changed to scene %s"%scene.name)
#            if scene.description:
#                print(scene.description)
#            else:
#                print("There is no description for this scene")
#            print("You can see:")
#            for i in scene.objects.values():
#                print(i.display_text)
        self.game.scene = scene
        if camera_point: scene.dx, scene.dy = camera_point
        if scene.name not in self.game.visited: self.game.visited.append(scene.name) #remember scenes visited
        if logging: log.debug("changing scene to %s"%scene.name)
        if self.game and self.game._headless: return #headless mode skips sound and visuals

        if self._ambient_sound: self._ambient_sound.stop()
#        if self.game.scene and self.game._window:
#            if self.game.scene._background:
#                self.game.scene._background.blit((0,0))
#                screen_blit(self.game.screen, self.game.scene.set_background(), (-self.game.scene.dx, -self.game.scene.dy))
#            else:
#                if logging: log.warning("No background for scene %s"%self.game.scene.name)
        #start music for this scene
 #       self._play_scene_music()
#        if game.scene._ambient_filename:
#            self._ambient_sound = self.game.mixer._sfx_play(game.scene._ambient_filename, loops=-1)


    def on_scene(self, scene):
        """ change the scene """
        if type(scene) in [str]:
            if scene in self.game._scenes:
                scene = self.game._scenes[scene]
            else:
                if logging: log.error("camera on_scene: unable to find scene %s"%scene)
                scene = self.game.scene

        #check for a precamera script to run
        if scene:
            precamera_fn = get_function(self.game, "precamera_%s"%slugify(scene.name))
            if precamera_fn: precamera_fn(self.game, scene, self.game.player)
        
        self._scene(scene)

        #check for a postcamera script to run
        if scene:
            postcamera_fn = get_function(self.game, "postcamera_%s"%slugify(scene.name))
            if postcamera_fn: postcamera_fn(self.game, scene, self.game.player)
        

class Mixer(metaclass=use_on_events): #the sound manager 
    def __init__(self, game):
        self.game = game
        self.name = "Default Mixer"
        self._busy = False

        self.music_break = 200000 #fade the music out every x milliseconds
        self.music_break_length = 15000 #keep it quiet for y milliseconds
        self.music_index = 0
        self._music_fname = None
        self._unfade_music = None # (channel_to_watch, new_music_volme)
        self._force_mute = False #override settings
        self._music_callback = None #callback for when music ends

        self._player = pyglet.media.Player()


    def _music_play(self, fname=None, loops=-1):
        if self._force_mute: return
        if fname: 
            if os.path.exists(fname):
                log.info("Loading music file %s"%fname)
#                music = pyglet.resource.media(filename)
                music = pyglet.media.load(fname)
                self._music_fname = fname
            else:
                log.warning("Music file %s missing."%fname)
                self._player.pause()
                return
        self.music_index = 0 #reset music counter
        if not self.game._headless: 
            self._player.queue(music)
            self._player.play()
#            self._player.on_eos = self._

    def on_music_play(self, fname=None, loops=-1):
        self._music_play(fname=fname, loops=loops)
        
    def _music_fade_out(self):
        self._player.pause()

    def _music_fade_in(self):
        if logging: log.warning("pyvida.mixer.music_fade_in fade not implemented yet")
        if self._force_mute: return
        try:
            self._player.play()
        except:
            pass

    def on_music_fade_out(self):
        self._music_fade_out()

    def on_music_fade_in(self):
        self._music_fade_in()
        
    def _music_stop(self):
        self._player.pause()

    def on_music_stop(self):
        self._music_stop()

    def on_music_volume(self, val):
        """ val 0.0 - 1.0 """
        self._player.volume = val

    def _sfx_play(self, fname=None, description=None, loops=0, fade_music=False, store=None):
        """
        store = True | False -> store the sfx as a variable on the Game object
        fade_music = False | 0..1.0 -> fade the music to <fade_music> level while playing this sfx
        description = <string> -> human readable description of sfx
        """
        sfx = None
        if store: setattr(self, store, sfx)
        if self.game and self.game._headless:  #headless mode skips sound and visuals
            if fname and not os.path.exists(fname):
                log.warning("Music sfx %s missing."%fname)
            return sfx 
        
        if fname: 
            if self.game.settings and self.game.settings.sfx_subtitles and description: #subtitle sfx
                d = "<sound effect: %s>"%description
                self.game.message(d)

            if os.path.exists(fname):
                log.info("Loading sfx file %s"%fname)
#                if pygame.mixer: 
#                    sfx = pygame.mixer.Sound(fname)
#                    if self.game.settings: sfx.set_volume(self.game.settings.sfx_volume)
            else:
                log.warning("Music sfx %s missing."%fname)
                return sfx
        if sfx and not self.game._headless: 
            #fade music if needed
            v = None
            #restore music if needed
            if v: self._unfade_music = (channel, v)
        if store: setattr(self, store, sfx)
        return sfx

    def on_sfx_play(self, fname=None, description=None, loops=0, fade_music=False, store=None):
        self._sfx_play(fname, description, loops, fade_music, store)            

    def on_sfx_stop(self, sfx=None):
        #if sfx: sfx.stop()
        pass

    def on_music_finish(self, callback=None):
        """ Set a callback function for when the music finishes playing """
        self._player.on_eos = callback


"""
Factories 
"""



class MenuFactory(object):
    """ define some defaults for a menu so that it is faster to add new items """
    def __init__(self, name, pos=(0,0), size=26, font=DEFAULT_MENU_FONT, colour=DEFAULT_MENU_COLOUR, layout=VERTICAL, anchor = LEFT, padding = 0):
        self.name = name
        self.position = pos
        self.size = size
        self.font = font
        self.colour = colour
        self.layout = layout
        self.padding = padding
        self.anchor = anchor
    

"""
Game class
"""


class Game(metaclass=use_on_events):
    def __init__(self, name="Untitled Game", version="v1.0", engine=VERSION_MAJOR, fullscreen=DEFAULT_FULLSCREEN, resolution=DEFAULT_RESOLUTION, fps=DEFAULT_FPS, afps=DEFAULT_ACTOR_FPS, projectsettings=None):

        self.name = name
        self.resolution = resolution
        self.fps = fps
        self.default_actor_fps =afps
        self.game = self
        self.player = None
        self.scene = None

        self.camera = Camera(self) #the camera object
        self.mixer = Mixer(self) #the sound mixer object
        self.menu = MenuManager(self) #the menu manager object
        self._menu_factories = {}

        self.directory_portals = DIRECTORY_PORTALS
        self.directory_items = DIRECTORY_ITEMS
        self.directory_scenes = DIRECTORY_SCENES
        self.directory_actors = DIRECTORY_ACTORS
        self.directory_emitters = DIRECTORY_EMITTERS
        self.directory_interface = DIRECTORY_INTERFACE

        #defaults
        self.font_speech = None
        self.font_speech_size = None

        self._actors = {}
        self._items = {}
        self._modals = []
        self._menu = []
        self._menus = [] #a stack of menus 
        self._scenes = {}
        self._gui = []
        self._window = pyglet.window.Window(*resolution)
        self._window.on_draw = self.pyglet_draw
        self._window.on_key_press = self.on_key_press
        self._window.on_mouse_motion = self.on_mouse_motion
        self._window.on_mouse_press = self.on_mouse_press
        self._window.on_mouse_release = self.on_mouse_release
        self._window.on_mouse_drag = self.on_mouse_drag

        #event handling
        self._waiting = False #If true, don't process any new events until the existing ones are no longer busy
        self._busy = False #game is never busy
        self._events = []
        self._event = None
        self._event_index = 0

        self._selected_options = [] #keep track of convo trees
        self.visited = [] #list of scene names visited

        #editor and walkthrough      
        self._modules = {}
        self._walkthrough = []
        self._walkthrough_index = 0 #our location in the walkthrough
        self._walkthrough_target = 0  #our target
        self._walkthrough_stored_state = None #TODO: for jumping back to a previous state in the game (WIP)
        self._headless = False #no user input or graphics

        self._output_walkthrough = False
        self._create_from_walkthrough = False
        self._catch_exceptions = True #engine will try and continue after encountering exception


        self._allow_editing = ENABLE_EDITOR
        self._editing = None
        self._editing_point = None #the set fns to pump in new x,y coords

        self._progress_bar_count = 0 #how many event steps in this progress block
        self._progress_bar_index = 0 #how far along the event list are we for this progress block
        self._progress_bar_renderer = None #if exists, call during loop



        self.parser = ArgumentParser()
        self.add_arguments()

        pyglet.clock.schedule(self.update) #the pyvida game scripting event loop

    def __getattr__(self, a): #game.__getattr__
        #only called as a last resort, so possibly set up a queue function
        if a == "actors": 
            print("game.actors deprecated, update")
            return self._actors
        if a == "items": 
            print("game.items deprecated, update")
            return self._items
        q = getattr(self, "on_%s"%a, None) if a[:3] != "on_" else None
        if q:
            f = create_event(q)
            setattr(self, a, f)
            return f
        else: #search through actors and items
            for s in [deslugify(a), a]: #try deslugged version or then full version
                if s in self._actors:
                    return self._actors[s]
                elif s in self._items:
                    return self._items[s]
    
        raise AttributeError
#        return self.__getattribute__(self, a)



    @property
    def w(self):
        return self._window.get_size()[0]

    @property
    def h(self):
        return self._window.get_size()[1]

    def on_key_press(self, symbol, modifiers):
        global use_effect
        if symbol == pyglet.window.key.F1:
            edit_object(self, list(self.scene._objects.values()), 0)
            self.menu_from_factory("editor", MENU_EDITOR)
        if symbol == pyglet.window.key.F2:
            game = self
            import pdb; pdb.set_trace()

    def on_mouse_motion(self,x, y, dx, dy):
        """ Change mouse cursor depending on what the mouse is hovering over """
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        """ If the mouse is over an object with a down action, switch to that action """
        pass

    def on_mouse_release(self, x, y, button, modifiers):
        """ Call the correct function depending on what the mouse has clicked on """
        y = self.game.resolution[1] - y #invert y-axis if needed
        for obj in self._modals:
            if obj.collide(x,y):
                print("collide with",obj.name)
                obj.trigger_interact()
                return
        #don't process other objects while there are modals
        if len(self._modals)>0: return 

        #try menu events
        for obj in self._menu:
            if obj.collide(x,y):
                obj.trigger_interact()
                return

        #finally, try scene objects
        for obj in self.scene._objects.values():
            if obj.collide(x,y):
                obj.trigger_interact()
                return


    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self._editing and self._editing_point: #we are editing something so send through the new x,y in pyvida format
            x,y = x, self.resolution[1] - y #invert for pyglet to pyvida
            if self._editing_point == self._editing.set_x: #set x, so use raw
                self._editing_point[0](x)
                self._editing_point[1](y)
            else: #displace the point by the object's x,y so the point is relative to the obj
                self._editing_point[0](x - self._editing.x)
                self._editing_point[1](y - self._editing.y)


    def add_arguments(self):
        """ Add allowable commandline arguments """
        self.parser.add_argument("-a", "--alloweditor", action="store_true", dest="allow_editor", help="Enable editor via F1 key")
#        self.parser.add_argument("-b", "--blank", action="store_true", dest="force_editor", help="smart load the game but enter the editor")
        self.parser.add_argument("-c", "--contrast", action="store_true", dest="high_contrast", help="Play game in high contrast mode (for vision impaired players)", default=False)
        self.parser.add_argument("-d", "--detailed <scene>", dest="analyse_scene", help="Print lots of info about one scene (best used with test runner)")
        self.parser.add_argument("-e", "--exceptions", action="store_true", dest="allow_exceptions", help="Switch off exception catching.")
        self.parser.add_argument("-f", "--fullscreen", action="store_true", dest="fullscreen", help="Play game in fullscreen mode", default=False)
        self.parser.add_argument("-g", action="store_true", dest="infill_methods", help="Launch script editor when use script missing", default=False)
        self.parser.add_argument("-H", "--headless", action="store_true", dest="headless", help="Run game as headless (no video)")
        self.parser.add_argument("-i", "--imagereactor", action="store_true", dest="artreactor", help="Save images from each scene (don't run headless)")
        self.parser.add_argument("-k", "--kost <background> <actor> <items>", nargs=3, dest="estimate_cost", help="Estimate cost of artwork in game (background is cost per background, etc)")
        self.parser.add_argument("-l", "--lowmemory", action="store_true", dest="memory_save", help="Run game in low memory mode")
        self.parser.add_argument("-m", "--matrixinventory", action="store_true", dest="test_inventory", help="Test each item in inventory against each item in scene", default=False)
        self.parser.add_argument("-o", "--objects", action="store_true", dest="analyse_characters", help="Print lots of info about actor and items to calculate art requirements", default=False)        
        self.parser.add_argument("-p", "--profile", action="store_true", dest="profiling", help="Record player movements for testing", default=False)        

        self.parser.add_argument("-R", "--random", action="store_true", dest="stresstest", help="Randomly deviate from walkthrough to stress test robustness of scripting")
        self.parser.add_argument("-r", "--resolution", dest="resolution", help="Force engine to use resolution WxH or (w,h) (recommended (1600,900))")
        self.parser.add_argument("-s", "--step", dest="target_step", help="Jump to step in walkthrough")
        self.parser.add_argument("-t", "--text", action="store_true", dest="text", help="Play game in text mode (for players with disabilities who use text-to-speech output)", default=False)
        self.parser.add_argument("-w", "--walkthrough", action="store_true", dest="output_walkthrough", help="Print a human readable walkthrough of this game, based on test suites.")
        self.parser.add_argument("-W", "--walkcreate", action="store_true", dest="create_from_walkthrough", help="Create a smart directory structure based on the walkthrough.")

        self.parser.add_argument("-x", "--exit", action="store_true", dest="exit_step", help="Used with --step, exit program after reaching step (good for profiling)")
        self.parser.add_argument("-z", "--zerosound", action="store_true", dest="mute", help="Mute sounds", default=False)        

    def walkthroughs(self, suites):
        """ use test suites to enable jumping forward """
        self._walkthrough = [i for sublist in suites for i in sublist]  #all tests, flattened in order

    def reset(self):
        """ reset all game state information, perfect for loading new games """
        self.scene = None
        self.player = None
        self._actors = {}
#        self._items = dict([(key,value) for key,value in self.items.items() if isinstance(value, MenuItem)])
        self._items = {}
        self._scenes = {}
#        self._emitters = {}                
#        if self.ENABLE_EDITOR: #editor enabled for this game instance
#            self._load_editor()


    def on_menu_from_factory(self, menu, items):
        """ Create a menu from a factory """
        if menu not in self._menu_factories: 
            log.error("Unable to find menu factory '{0}'".format(menu))
            return
        factory = self._menu_factories[menu]
        #guesstimate width of whole menu so we can do some fancy layout stuff

        new_menu = []
        min_y = 0
        min_x = 0
        total_w = 0
        total_h = 0
        for i, item in enumerate(items):
            if item[0] in self._items.keys():
                obj = get_object(self.game, item[0])
                obj.interact = item[1]
            else:
                obj = Text(item[0], font=factory.font, colour=factory.colour, size=factory.size)
                obj.game = self
                obj.interact = item[1] #set callback
            kwargs = item[2] if len(item)>2 else {}
            for k, v in kwargs.items():
                setattr(obj, k, v)
 #               if k == "key": obj.key = get_keycode(v)
#            if "text" in kwargs.keys(): obj.update_text() #force update on MenuText

            self._add(obj)
            new_menu.append(obj)
            w,h = obj.clickable_area.w, obj.clickable_area.h
            total_w += w + factory.padding
            total_h += h + factory.padding
            if h > min_y: min_y = obj.clickable_area.h
            if w > min_x: min_x = obj.clickable_area.w

        total_w -= factory.padding
        total_h -= factory.padding
        #calculate the best position for the item        
        if factory.anchor == LEFT:
            x,y = factory.position
        elif factory.anchor == RIGHT:
            x,y = factory.position[0]-total_w, factory.position[1]
        elif factory.anchor == CENTER:
            x,y = factory.position[0]-(total_w/2), factory.position[1]
        
        for obj in new_menu:
            w,h = obj.clickable_area.w, obj.clickable_area.h
            if factory.layout == HORIZONTAL:
                dx, dy = w + factory.padding, 0
            elif factory.layout == VERTICAL:
                dx, dy = 0, h + factory.padding
            obj.x, obj.y = x, y
            x += dx
            y += dy

    def on_smart(self, player=None, player_class=Actor, draw_progress_bar=None, refresh=False, only=None): #game.smart
        self._smart(player, player_class, draw_progress_bar, refresh, only)

    def _smart(self, player=None, player_class=Actor, draw_progress_bar=None, refresh=False, only=None): #game.smart
        """ cycle through the actors, items and scenes and load the available objects 
            it is very common to have custom methods on the player, so allow smart
            to use a custom class
            player is the the first actor the user controls.
            player_class can be used to override the player class with a custom one.
            draw_progress_bar is the fn that handles the drawing of a progress bar on this screen
            refresh = reload the defaults for this actor (but not images)
        """
        if draw_progress_bar:
            self._progress_bar_renderer = draw_progress_bar
            self._progress_bar_index = 0
            self._progress_bar_count = 0

        portals = []
        for obj_cls in [Actor, Item, Emitter, Portal, Scene]:
            dname = "directory_%ss"%obj_cls.__name__.lower()
            if not os.path.exists(getattr(self, dname)): continue #skip directory if non-existent
            for name in os.listdir(getattr(self, dname)):
                if draw_progress_bar: #estimate the size of the loading
                    self._progress_bar_count += 1
                if only and name not in only: continue #only load specific objects 
                if logging: log.debug("game.smart loading %s %s"%(obj_cls.__name__.lower(), name))
                #if there is already a non-custom Actor or Item with that name, warn!
                if obj_cls == Actor and name in self._actors and self._actors[name].__class__ == Actor and not refresh:
                    if logging: log.warning("game.smart skipping %s, already an actor with this name!"%(name))
                elif obj_cls == Item and name in self._items  and self._items[name].__class__ == Item and not refresh:
                    if logging: log.warning("game.smart skipping %s, already an item with this name!"%(name))
                else:
                    if not refresh: #create a new object
                        if type(player)==str and player == name:
                            a = player_class(name)
                        else:
                            a = obj_cls(name)
                        self._add(a)
                    else: #if just refreshing, then use the existing object
                        a = self._actors.get(name, self._items.get(name, self._scenes.get(name, None)))
                        if not a: import pdb; pdb.set_trace()
                    a.smart(self)
                    if a.__class__ == Portal: portals.append(a.name)                  
        for pname in portals: #try and guess portal links
            if draw_progress_bar: self._progress_bar_count += 1
            links = pname.split("_to_")
            guess_link = None
            if len(links)>1: #name format matches guess
                guess_link = "%s_to_%s"%(links[1].lower(), links[0].lower())
            if guess_link and guess_link in self._items:
                self._items[pname].link = self._items[guess_link]
            else:
                if logging: log.warning("game.smart unable to guess link for %s"%pname)
            self._items[pname].auto_align() #auto align portal text
        if type(player) in [str]: player = self._actors[player]
        if player: self.player = player

    def check_modules(self):
        """ poll system to see if python files have changed """
        modified = False
#        if 'win32' in sys.platform: # don't allow on windows XXX why?
#            return modified
        for i in self._modules.keys(): #for modules we are watching
            if not i in sys.modules:
                log.error("Unable to reload module %s (not in sys.modules)"%i)
                continue
            fname = sys.modules[i].__file__
            fname, ext = os.path.splitext(fname)
            if ext == ".pyc": ext = ".py"
            fname = "%s%s"%(fname, ext)
            ntime = os.stat(fname).st_mtime #check the modified timestamp
            if ntime > self._modules[i]: #if modified since last check, return True
                self._modules[i] = ntime
                modified = True
        return modified


    def set_modules(self, modules):        
        """ when editor reloads modules, which modules are game related? """
        for i in modules:
            self._modules[i] = 0 
        if self._allow_editing: #if editor is available, watch code for changes
            self.check_modules() #set initial timestamp record

    def reload_modules(self, modules=None):
        """
        Reload all the interact/use/look functions from the tracked modules (game._modules)

        modules -- use the listed modules instead of game._modules
        """

        print("RELOAD MODULES")
        #clear signals so they reload
        for i in [post_interact, pre_interact, post_use, pre_use, pre_leave, post_arrive]:
            i.receivers = []
        
        #reload modules
        module = "main" if android else "__main__" #which module to search for functions
        modules = modules if modules else self._modules.keys()
        if type(modules) != list: modules = [modules]
        for i in self._modules.keys():
            try:
                imp.reload(sys.modules[i])
            except:
                log.error("Exception in reload_modules")
                print(sys.modules)
                print("\nError reloading %s\n"%sys.modules[i])
                if traceback: traceback.print_exc(file=sys.stdout)
                print("\n\n")
            for fn in dir(sys.modules[i]): #update main namespace with new functions
                new_fn = getattr(sys.modules[i], fn)
                if hasattr(new_fn, "__call__"): setattr(sys.modules[module], new_fn.__name__, new_fn)

        #XXX update .uses{} values too.
        for i in (list(self._actors.values()) + list(self._items.values())):
            if i.interact: 
                if type(i.interact) != str:
                    new_fn = get_function(self.game, i.interact.__name__)
                    if new_fn: i.interact = new_fn #only replace if function found, else rely on existing fn
            if i.name == "Brutus Ship": import pdb; pdb.set_trace()
            if i.look: 
                if type(i.look) != str:
                    new_fn = get_function(self.game, i.look.__name__)
                    if new_fn: i.look = new_fn #only replace if function found, else rely on existing fn

        log.info("Editor has done a module reload")


    def run(self, splash=None, callback=None, icon=None):
        #event_loop.run()
        options = self.parser.parse_args()    
        if options.mute == True:
            self.mixer._force_mute = True
        if options.target_step: #switch on test runner to step through walkthrough
            if options.target_step.isdigit():
                self._walkthrough_target = int(options.target_step) #automatically run to <step> in walkthrough
            else:
                pass
                log.error("TODO: take step labels are walkthrough targets")
#                for step in self._walkthrough:                      
                    #self.jump_to_step = options.step
        if options.exit_step:
            self.exit_step = True                
        if options.headless: 
            self.on_set_headless(True)

        if splash:
            scene = Scene(splash, self)
            scene.set_background(splash)
            self.add(scene)
            self.camera.scene(scene)

        if callback: callback(0, self)
        pyglet.app.run()

    def queue_event(self, event, *args, **kwargs):
        self._events.append((event, args, kwargs))

    def _process_walkthrough(self):
        """ Do a step in the walkthrough """
        walkthrough = self._walkthrough[self._walkthrough_index]
        function_name = walkthrough[0].__name__ 
        self._walkthrough_index += 1    
        print("AUTO WALKTHROUGH", walkthrough)
        if function_name == "interact":
            print("trigger interact", self._walkthrough_target, self._walkthrough_index, walkthrough[1])
            button = pyglet.window.mouse.LEFT
            modifiers = 0
            obj = get_object(self, walkthrough[1])
            x, y = obj.clickable_area.center
            obj.trigger_interact()
#                self._window.dispatch_event('on_mouse_release', x, self.resolution[1] - y, button, modifiers)
        elif function_name == "description":
            pass
        if self._walkthrough_index > self._walkthrough_target:
            if self._headless: self._headless = False
            print("FINISHED WALKTHROUGH")
            self.player.says(gettext("Let's play."))

    def _handle_events(self):
        """ Handle game events """
        safe_to_call_again = False #is it safe to call _handle_events immediately after this?
        if self._waiting: 
            """ check all the Objects with existing events, if any of them are busy, don't process the next event """
            none_busy = True
            for event in self._events[:self._event_index]: #event_index is point to the game.wait event at the moment
                obj = event[1][0] #first arg is always the object that called the event
                if obj._busy == True: 
                    none_busy = False
            if none_busy == True: 
                self._waiting = False #no prior events are busy, so stop waiting
            else:
                return safe_to_call_again #game is waiting on an actor, so leave
        done_events = 0
        del_events = 0
        #if there are events and we are not at the end of them
        if len(self._events)>0: 
            if self._event_index>0:
                for event in self._events[:self._event_index]: #check the previous events' objects, delete if not busy
                    if event[1][0]._busy == False:
                        del_events += 1
                        self._events.remove(event)
                        self._event_index -= 1

            if self._event_index < len(self._events):
                #possibly start the current event
                e = self._events[self._event_index] #stored as [(function, args))]
                obj = e[1][0]
                if obj._busy: return safe_to_call_again#don't do this event yet if the owner is busy
                self._event = e
#                print("Start",e[0], e[1][0].name, datetime.now(), e[1][0]._busy)
                done_events += 1
                print("DOING",e)
                e[0](*e[1], **e[2]) #call the function with the args and kwargs
                self._event_index += 1

                #if, after running the event, the obj is not busy, then it's OK to do the next event immediately.
                if not obj._busy:
                    safe_to_call_again = True
                    return safe_to_call_again
                    print("Game not busy, events not busy, and the current object is not busy, so do another event", len(self._events),depth)

            #if self._event_index<len(self._events)-1: self._event_index += 1

        #auto trigger an event from the walkthrough if needed and nothing else is happening
        if done_events == 0 and del_events == 0 and self._walkthrough_target >= self._walkthrough_index: 
            self._process_walkthrough()
        return safe_to_call_again
#        print("Done %s, deleted %s"%(done_events, del_events))  


    def update(self, dt, single_event=False): #game.update
        """ Run update on scene objects """
        scene_objects = self.scene._objects.values() if self.scene else []
        for items in [scene_objects, self._menu, self._modals]:
            for item in items:
                if hasattr(item, "_update"): item._update(dt)

        if single_event:
            self._handle_events() #run the event handler only once
        else:
            while self._handle_events(): #loop while there are events safe to process
                pass

        if self._headless and self._walkthrough_target >= self._walkthrough_index and len(self._modals)>0:
            self._process_walkthrough()

    def pyglet_draw(self): #game.draw
        """ Draw the scene """
        if not self.scene: return
#        self.scene.pyglet_draw()
        if self.scene.background:
            self._window.clear()
            pyglet.gl.glColor4f(1.0, 1.0, 1.0, 1.0) # undo alpha for pyglet drawing            
            self.scene.background.blit(self.scene.x, self.scene.y)
        else:
            print("no background")

        objects = sorted(self.scene._objects.values(), key=lambda x: x.y, reverse=False)
        for item in objects:
            item.pyglet_draw()
        #draw scene foregrounds
        for item in self.scene._foreground:
            item.pyglet_draw()

        for item in self._menu:
            item.pyglet_draw()

        for modal in self._modals:
            modal.pyglet_draw()

    def _add(self, objects, replace=False): #game.add
        objects_iterable = [objects] if not isinstance(objects, Iterable) else objects

        for obj in objects_iterable:
            #check if it is an existing object
            if obj in self._actors.values() or obj in self._items.values() or obj in self._scenes.values():
                if replace == False: 
                    continue
                elif replace == True:
                    print("REPLACING",obj.name)

            try:
                obj.game = self
            except:
                import pdb; pdb.set_trace()
            if isinstance(obj, Scene):
                self._scenes[obj.name] = obj
#                if self.analyse_scene == obj.name: 
#                    self.analyse_scene = obj
#                    obj._total_actors = [] #store all actors referenced in this scene
#                    obj._total_items = []
            elif isinstance(obj, MenuFactory):
                self._menu_factories[obj.name] = obj
            elif isinstance(obj, Portal):
                self._items[obj.name] = obj
            elif isinstance(obj, Item):
                self._items[obj.name] = obj
            elif isinstance(obj, Actor):
                self._actors[obj.name] = obj
        return objects


    def add(self, objects, replace=False): #game.add (not an event driven function)
        return self._add(objects, replace=replace)

    def add_font(self, filename, fontname):
        font = get_font(self, filename, fontname)
        _pyglet_fonts[filename] = fontname 

    def set_interact(self, actor, fn): #game.set_interact
        """ helper function for setting interact on an actor """
        actor = get_object(self, actor)
        actor.interact = fn


    def _save_state(self, state=""): 
        game = self
        if state=="": return
        sfname = os.path.join(self.scene.directory, state)
        sfname = "%s.py"%sfname
        keys = [x.name for x in game.scene._objects.values() if not isinstance(x, Portal) and x != game.player]
        objects = '\",\"'.join(keys)
        has_emitter = False
        for name, obj in game.scene._objects.items():
            if isinstance(obj, Emitter): has_emitter=True
        
        if not os.path.isdir(os.path.dirname(sfname)):
            game.player.says("Warning! %s does not exist"%sfname)
            return
        with open(sfname, 'w') as f:
            f.write("# generated by ingame editor v0.2\n\n")
            f.write("def load_state(game, scene):\n")
            f.write('    from pyvida import WalkArea, Rect\n')
            f.write('    import os\n')
            if has_emitter: 
                f.write('    import copy\n')
                f.write('    from pyvida import Emitter\n')
#                        f.write('    game.stuff_events(True)\n')
            f.write('    scene.clean(["%s"])\n'%objects) #remove old actors and items
            if game.scene._music_filename:
                f.write('    scene.music("%s")\n'%game.scene._music_filename)
            if game.scene._ambient_filename:
                f.write('    scene.ambient("%s")\n'%game.scene._ambient_filename)
#            f.write('    scene._walkareas = [')
#            for w in game.scene._walkareas:
#                walkarea = str(w.polygon.vertexarray)
#                f.write('WalkArea().smart(game, %s),'%(walkarea))
#            f.write(']\n')
            for name, obj in game.scene._objects.items():
                slug = slugify(name).lower()
                if obj != game.player and obj._editing_save == True:
                    txt = "items" if isinstance(obj, Item) else "actors"
                    if isinstance(obj, Emitter):
                        em = str(obj.summary)
                        f.write("    em = %s\n"%em)
                        f.write('    %s = Emitter(**em).smart(game)\n'%slug)
                    else:
                        f.write('    %s = game._%s["%s"]\n'%(slug, txt, name))
                    r = obj._clickable_area
                    f.write('    %s.reclickable(Rect(%s, %s, %s, %s))\n'%(slug, r.x, r.y, r.w, r.h))
                    r = obj._solid_area
                    f.write('    %s.resolid(Rect(%s, %s, %s, %s))\n'%(slug, r.x, r.y, r.w, r.h))
                    #if not (obj.allow_draw and obj.allow_update and obj.allow_interact and obj.allow_use and obj.allow_look):
                    f.write('    %s.usage(%s, %s, %s, %s, %s)\n'%(slug, obj.allow_draw, obj.allow_update, obj.allow_look, obj.allow_interact, obj.allow_use))
                    f.write('    %s.rescale(%0.2f)\n'%(slug, obj.scale))
                    f.write('    %s.reanchor((%i, %i))\n'%(slug, obj._ax, obj._ay))
                    f.write('    %s.restand((%i, %i))\n'%(slug, obj._sx, obj._sy))
                    f.write('    %s.rename((%i, %i))\n'%(slug, obj._nx, obj._ny))
                    f.write('    %s.retext((%i, %i))\n'%(slug, obj._tx, obj._ty))
                    f.write('    %s.relocate(scene, (%i, %i))\n'%(slug, obj.x, obj.y))
                    if obj._parent:
                        f.write('    %s.reparent(\"%s\")\n'%(slug, obj._parent.name))
                    if obj.action and obj.action.name != "idle":
                        f.write('    %s.do("%s")\n'%(slug, obj.action.name))
                    if isinstance(obj, Portal): #special portal details
                        ox,oy = obj._ox, obj._oy
                        if (ox,oy) == (0,0): #guess outpoint
                            ox = -150 if obj.x < game.resolution[0]/2 else game.resolution[0]+150
                            oy = obj.sy
                        f.write('    %s.reout((%i, %i))\n'%(slug, ox, oy))
                else: #the player object
                    f.write('    #%s = game._actors["%s"]\n'%(slug, name))                            
                    f.write('    #%s.reanchor((%i, %i))\n'%(slug, obj._ax, obj._ay))
                    r = obj._clickable_area
                    f.write('    #%s.reclickable(Rect(%s, %s, %s, %s))\n'%(slug, r.x, r.y, r.w, r.h))

                    if name not in self.scene.scales:
                        self.scene.scales[name] = obj.scale
                    for key, val in self.scene.scales.items():
                        if key in self._actors:
                            val = self._actors[key]
                            f.write('    scene.scales["%s"] = %0.2f\n'%(val.name, val.scale))
                    f.write('    scene.scales["actors"] = %0.2f\n'%(obj.scale))




    def load_state(self, scene, state):
        self._load_state(scene, state)


    def _load_state(self, scene, state):

        """ a queuing function, not a queued function (ie it adds events but is not one """
        """ load a state from a file inside a scene directory """
        """ stuff load state events into the start of the queue """
        if type(scene) in [str]:
            if scene in self._scenes:
                scene = self._scenes[scene]
            else:
                if logging: log.error("load state: unable to find scene %s"%scene)
                return
        sfname = os.path.join(self.directory_scenes, os.path.join(scene.name, state))
        sfname = "%s.py"%sfname
        variables= {}
        if not os.path.exists(sfname):
            if logging: log.error("load state: state not found for scene %s: %s"%(scene.name, sfname))
        else:
            if logging: log.debug("load state: load %s for scene %s"%(sfname, scene.name))
            scene._last_state = sfname
#            execfile("somefile.py", global_vars, local_vars)
            with open(sfname) as f:
                code = compile(f.read(), sfname, 'exec')
                exec(code, variables)

            variables['load_state'](self, scene)


    def on_wait(self):
        """ Wait for all scripting events to finish """
        self._waiting = True
        return  

    def on_splash(self, image, callback, duration=None, immediately=False):
        """ show a splash screen then pass to callback after duration 
        """
        if logging: log.warning("game.splash ignores duration and clicks")
        if self._allow_editing: duration = 0.1 #skip delay on splash when editing
        scene = Scene(image, game=self)
        scene._set_background(image)
        self._busy = True #set Game object to busy
        self._waiting = True #make game wait until splash is finished
        #add scene to game, change over to that scene
        self.add(scene)
        self.camera._scene(scene)
        if scene._background:
            self._background.blit(0,0)

        def splash_finish(d, game):
            self._busy = False #finish the event
            callback(d, game)
        if callback:
            if not duration:
                splash_finish(0, self)
            else:
                pyglet.clock.schedule_once(splash_finish, duration, self)

    def on_relocate(self, obj, scene, destination): #game.relocate
        obj = get_object(self.game, obj)
        scene = get_object(self.game, scene)
        destination = get_point(self.game, destination)
        obj._relocate(scene, destination)

    def on_set_headless(self, v):
        self._headless = v

    def on_set_menu(self, *args):
        """ add the items in args to the menu """
        args = list(args)
        args.reverse()
        for i in args:
            if type(i) not in [str]: i = i.name
            if i in self._items.keys(): 
                self._menu.append(self._items[i])
            else:
                if logging: log.error("Menu item %s not found in Item collection"%i)
        if logging: log.debug("set menu to %s"%[x.name for x in self._menu])

"""
Editor stuff

        self._editable = [
            ("position", (self.x, self.y),  (int, int)),
            ("anchor", (self.ax, self.ay), (int, int)),
            ("interact", self.interact, str),
            ("allow_draw", self._allow_draw, bool), # ( "allow_update", "allow_use", "allow_interact", "allow_look"]        
            ]
"""


class Navigator(tk.Toplevel):
    def __init__(self, app, parent, game):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.app = app
        self.game = game
        self.createWidgets()
        self.title("Navigator")


    def createWidgets(self):
        self.prev_button = tk.Button(self, text='<-', command=self.prev).grid(column=0, row=0)
        self.edit_button = tk.Button(self, text='Edit', command=self.create_editor)
        self.edit_button.grid(column=1, row=0)
        self.next_button = tk.Button(self, text='->', command=self.next).grid(column=2, row=0)
        def save_state(*args, **kwargs):
            d = tk.filedialog.SaveFileDialog(self.parent)
            pattern, default, key = "*.py", "", None
            fname = d.go(self.game.scene.directory, pattern, default, key)
            if fname is None:
                return
            else:
                print("SAVE STATE")
                state_name = os.path.splitext(os.path.basename(fname))[0]
                self.game._save_state(state_name)
#            game.user_input("What is the name of this %s state to save (no directory or .py)?"%self.scene.name, e_save_state)
#            print(args, kwargs)
        def load_state(*args, **kwargs):
            print(args, kwargs)
#            self.game._load_state()
            d = tk.filedialog.LoadFileDialog(self.parent)
            pattern, default, key = "*.py", "", None
            fname = d.go(self.game.scene.directory, pattern, default, key)
            if fname is None:
                return
            else:
                state_name = os.path.splitext(os.path.basename(fname))[0]
                print("STATE_NAME",state_name)
                self.game.load_state(self.game.scene, state_name)
        self.state_save_button = tk.Button(self, text='save state', command=save_state).grid(column=0, row=1)
        self.state_load_button = tk.Button(self, text='load state', command=load_state).grid(column=1, row=1)

    def _navigate(self, delta):
        obj = self.app.objects[self.app.index]
        obj.show_debug = False
        self.app.index += delta
        if self.app.index < 0: self.app.index = len(self.app.objects)-1
        if self.app.index >= len(self.app.objects): self.app.index = 0
        print(self.app.index, [(i,x.name) for i,x in enumerate(self.app.objects)])
        obj = self.app.objects[self.app.index]
        obj.show_debug = True
        self.edit_button["text"] = obj.name

    def prev(self):
        self._navigate(-1) #decrement navigation

    def next(self):
        self._navigate(1) #increment navigation

    def create_editor(self):
        obj = self.app.objects[self.app.index]
        self.app.create_editor(obj)
    

class Editor(tk.Toplevel):
    def __init__(self, app, parent, game, obj):
        tk.Toplevel.__init__(self, parent)
        self.title(obj.name)
        self.frame = tk.Frame(parent)
        self.app = app
        self.obj = obj
        self.game = game
        self._editing = tk.StringVar()
        self._editing.set("Nothing")
        self.createWidgets()
        self.lift(aboveThis=parent)
        parent.attributes("-topmost", 1)

    def close_editor(self):
        obj = self.app.objects[self.app.index]
        obj.show_debug = False
        self.destroy()

    def selected(self):
        print(self._editing.get())
        for editable in self.obj._editable:
            if self._editing.get() == editable[0]: #this is what we want to edit now.
                label, get_attrs, set_attrs, types = editable
                self.game._editing = self.obj
                self.game._editing_point = set_attrs

    def createWidgets(self):
        for i, editable in enumerate(self.obj._editable):
            label, get_attrs, set_attrs, types = editable
            tk.Radiobutton(self, text=label, variable=self._editing, value=label, indicatoron=0, command=self.selected).grid(row=i, column=0)
            if type(types) == tuple: #assume two ints
                e = tk.Entry(self)
                e.grid(row=i, column=1)
                e.insert(0, get_attrs[0]())
                e = tk.Entry(self)
                e.grid(row=i, column=2)
                e.insert(0, get_attrs[1]())
            elif types == str:
                e = tk.Entry(self)
                e.grid(row=i, column=1, columnspan=2)
#                if get_attrs: e.insert(0, get_attrs())
            elif types == bool:
                tk.Checkbutton(self, variable=get_attrs()).grid(row=i, column=1, columnspan=2)

        self.QUIT = tk.Button(self)
        self.QUIT["text"] = "Close"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.close_editor
        self.QUIT.grid(row=i+1)


class MyTkApp(threading.Thread):
    def __init__(self, game, objects, index, callback=None):
        threading.Thread.__init__(self)
        self.game = game
        self.objects = objects
        self.index = index
        self.callback = callback
        self._editors = []
        self.start()

    def create_editor(self, obj):
        self._editors.append(Editor(self, self.parent, self.game, obj))
    def run(self):
        self.parent=tk.Tk()
        self.parent.protocol("WM_DELETE_WINDOW", self.callback)
        self.navigator = Navigator(self, self.parent, self.game)
        self.navigator.geometry('400x100+{}+{}'.format(self.game.resolution[0]-400, 0))
#        self.create_editor(self.objects[self.index])
        #create close all button
        self.close = tk.Button(self.parent)
        self.close["text"] = "Close Editor"
        self.close["command"] =  self.callback
        self.close.grid()

        self.parent.mainloop()

def edit_object(game, objects, index):
    """ Open a tk editor for this object and import the values back into the project when done """
    if index < len(objects):
        obj = game._editing = objects[index]
        obj.show_debug = True
    def close_editor():
        app.parent.destroy()
    app = MyTkApp(game, objects, index, close_editor)
