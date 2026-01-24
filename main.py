from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.clock import Clock
import math
import random




class Game(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player=Player()
        self.joystick=JoyStick()
        self.AttackJoystick=AttackJoystick()
        self.AttackJoystick.pos = (Window.width - 160, 20)
        self.add_widget(self.AttackJoystick)
        self.add_widget(self.joystick)
        self.add_widget(self.player)
        self.player.center = self.center
        self.player.health=100
        self.player.score=0
       
        #enemy
        self.enemies=[]
        self.attacks=[]
        self.counter=0
        if(self.counter<15):
            self.enemy=Clock.schedule_interval(self.spawnEnemy,5)
        if(self.counter>15):
            self.enemy=self.spawnBoss()

        Clock.schedule_interval(self.update,1/60)

        
    def spawnAtttck(self,dt):
        direction=self.AttackJoystick.vector
        if direction == (0,0):
            direction = (0,1)
        attack=Attack(direction=direction)
        attack.pos=(self.player.x,self.player.y)
        self.add_widget(attack)
        self.attacks.append(attack)
        

    def spawnEnemy(self,dt):
        if Window.width <= 0 or Window.height <= 0:
            return
        self.counter +=1
        print(self.counter)
        enemy=Enemy()
        enemy.type={ 1:{"size":30,"health":100,"speed":1,"damage":10},2:{"size":50,"health":150,"speed":0.5,"damage":20}}
        num=random.randint(1,2)
        print(num)
        print((enemy.type[num]))
        enemy.size = (enemy.type[num]["size"],enemy.type[num]["size"])
        enemy.boss=False
        enemy.health=enemy.type[num]["health"]
        enemy.speed=enemy.type[num]["speed"]
        enemy.damage=enemy.type[num]["damage"]
        max_x=max(0,Window.width-enemy.width)
        enemy.pos=(random.uniform(0,max_x),Window.height)
        self.add_widget(enemy)
        self.enemies.append(enemy)
    
    def spawnBoss(self,dt):
        if Window.width <= 0 or Window.height <= 0:
            return
        enemy=Enemy()
        enemy.type={ 1:{"size":70,"health":200,"speed":1,"damage":25},2:{"size":70,"health":200,"speed":0.5,"damage":25}}
        num=random.randint(1,2)
        print(num)
        print((enemy.type[num]))
        enemy.size = (enemy.type[num]["size"],enemy.type[num]["size"])
        enemy.boss=True
        enemy.boss.health=enemy.type[num]["health"]
        enemy.speed=enemy.type[num]["speed"]
        enemy.damage=enemy.type[num]["damage"]
        max_x=max(0,Window.width-enemy.width)
        enemy.pos=(random.uniform(0,max_x),Window.height)
        self.add_widget(enemy)
        self.enemies.append(enemy)
        





    def update(self,dt):
        #player
            #movement
        vx,vy=self.joystick.vector
    
        speed=4
        self.player.x +=vx*speed
        self.player.y +=vy*speed

        self.player.x=max(0,min(self.player.x,Window.width-self.player.width))
        self.player.y=max(0,min(self.player.y,Window.height-self.player.height))

            #health
        if self.player.health <= 0:
            print("Game Over!!")

           

            #attack
        for attack in self.attacks:
            attack.x +=attack.vx*attack.speed
            attack.y +=attack.vy*attack.speed
            if attack.y > Window.height:
                self.remove_widget(attack)
                self.attacks.remove(attack)
       
         #enemy
        for enemy in self.enemies:
            #movement
            enemy_x=self.player.x-enemy.x
            enemy_y=self.player.y-enemy.y
            enemy_distance=math.sqrt(enemy_x**2+enemy_y**2)
            if enemy_distance > 0:
                enemy_x /=enemy_distance  #used for normalizing from -1 to 1 using sin and cos 
                enemy_y /=enemy_distance
                enemy.x +=enemy_x*enemy.speed
                enemy.y +=enemy_y*enemy.speed

            #colloison with player
            if enemy.collide_widget(self.player):
                self.player.health -=enemy.damage
                print(self.player.health)
                self.remove_widget(enemy)
                self.enemies.remove(enemy)
            #colloison with attack
            for attack in self.attacks:
                if enemy.collide_widget(attack):
                        if (enemy.boss==False):
                            enemy.health -=attack.damage
                            self.remove_widget(attack)
                            self.attacks.remove(attack)
                            print(enemy.health)
                            if enemy.health <=0:
                                self.remove_widget(enemy)
                                self.enemies.remove(enemy)
                                self.player.score +=1
                        if(enemy.boss==True):
                            enemy.boss.health -=attack.damage
                            self.remove_widget(attack)
                            self.attacks.remove(attack)
                            print(enemy.boss.health)
                            if enemy.boss.health <=0:
                                self.remove_widget(enemy)
                                self.enemies.remove(enemy)
                                self.player.score +=10
                                self.counter=0

                



class JoyStick(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.radius=60
        self.radius_knob=25
        self.active=False
        self.vector=(0,0)
    
    def on_touch_move(self,touch):
        if not self.collide_point(touch.x,touch.y):
            return
        
        dx=touch.x-self.center_x
        dy=touch.y-self.center_y

        distance=math.sqrt(dx**2+dy**2)
        
        if distance >self.radius:
            dx= dx/distance * self.radius  #used for normalizing from -1 to 1 using sin and cos 
            dy= dy/distance * self.radius
        self.vector=(dx/self.radius,dy/self.radius) 
        return True
    
    def on_touch_up(self, touch):
        self.vector = (0, 0)

class AttackJoystick(Widget):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.radius=60
        self.knob_radius=25
        self.vector=(0,0)
        self.shooting=False
        
    def on_touch_move(self,touch):
            if not self.collide_point(touch.x,touch.y):
                return
            dx=touch.x-self.center_x
            dy=touch.y-self.center_y

            distance=math.sqrt(dx**2+dy**2)
            if distance >self.radius:
                dx= dx/distance * self.radius  #used for normalizing from -1 to 1 using sin and cos 
                dy= dy/distance * self.radius
            self.vector=(dx/self.radius,dy/self.radius) 

            if not self.shooting:
                self.shooting=True
                self.parent.player.attack=Clock.schedule_interval(self.parent.spawnAtttck,0.5)

            return True
        
    def on_touch_up(self,touch):
            self.vector=(0,0)
            if self.shooting:
                self.parent.player.attack.cancel()
                del self.parent.player.attack
                self.shooting=False
            

            



class Player(Widget):
    pass

class Enemy(Widget):
    pass

class Attack(Widget):
    def __init__(self,direction=(0,1),**kwargs):
        super().__init__(**kwargs)
        dx,dy=direction
        length=math.sqrt(dx**2+dy**2)
        if length ==0:
            self.vx,self.y=0,1
        else:
            self.vx =dx/length
            self.vy =dy/length
        self.speed=7
        self.damage=50


class Escape(App):
    def build(self):
        return Game()
if __name__ == '__main__':
    Escape().run()