from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import NumericProperty,ListProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.relativelayout import RelativeLayout
import math
import random




class Game(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_paused=False
        self.ui_layer=GameUI()
        self.add_widget(self.ui_layer)

        self.player=Player()
        self.joystick=JoyStick(size_hint=(None, None),size=(120, 120),pos_hint={"x": 0.05, "y": 0.05})
        self.AttackJoystick=AttackJoystick(size_hint=(None, None),size=(120, 120),pos_hint={"right": 0.95, "y": 0.05})
        self.AttackJoystick.pos = (Window.width - 160, 20)
        self.add_widget(self.AttackJoystick)
        self.add_widget(self.joystick)
        self.add_widget(self.player)
        self.player.center = self.center
        self.player.healthBar=HealthBar(max_health=self.player.max_health,health=self.player.health, size_hint=(None, None),size=(200, 20),pos_hint={"x": 0.02, "top": 0.98})
        self.add_widget(self.player.healthBar)
        self.player.gun=Gun(owner=self.player)
        self.add_widget(self.player.gun)
        self.player.guns={"assualt":{"damage": 25,"range": 800,"magazine": 30,"ammo":30,"rate": 0.25,"reload": 1.5}}
        self.powerUps=[]
        self.powerUp_type={ 1:{"type":"health","size":24,"color":[0,1,0,1],"symbol":"+"},
                            2:{"type":"sheild","size":24,"color":[0,0.6,1,1],"symbol":"S"},
                            3:{"type": "damage_booster", "size": 24, "color": [1,0,0,1], "symbol": "D"},
                            4:{"type": "nuke", "size": 24, "color": [1,0.5,0,1], "symbol": "N"},
                            5:{"type": "freeze", "size": 24, "color": [0.5,0.8,1,1], "symbol": "F"}}
        self.gunList=[      
                            {"name": "Gun: Shotgun", "type": "shotgun",  "min_wave": 1},
                            {"name": "Gun: machine", "type": "machine",  "min_wave": 2},
                            {"name": "Gun: sniper", "type": "sniper",  "min_wave": 2},
                     ]
        self.upgrades = [
                            {"target":"player","name": "Regen +1", "type": "regen", "value": 1,"count":0},
                            {"target":"player","name": "Max Health +20", "type": "max_health", "value": 20,"count":0},
                            {"target":"player","name": "Heal 25", "type": "health", "value": 25,"count":0},
                            
                        ]
        
        self.game_paused = False
        #enemy
        self.enemies=[]
        self.attacks=[]
        self.Enemyattacks=[]
        self.remove_attack=[]
        self.remove_enemyAttack=[]
        self.remove_enemy=[]
        self.remove_powerup=[]
        self.counter=0
        self.bossWave=False
        self.bossAlive=0
        self.maxBoss=1
        self.wave=""
        self.wave_count=0
        self.enemies_per_wave=0
       
        self.enemy=Clock.schedule_interval(self.spawnEnemy,5)
        self.powerUp=Clock.schedule_interval(self.spawnPowerUp,5)
        Clock.schedule_interval(self.playerRegen,5)
        Clock.schedule_interval(self.update,1/60)
    def playerRegen(self,dt):
        if self.player.health<self.player.max_health:
            self.player.health +=self.player.regen

    def show_menu(self):
        self.game_paused=True
        for gun in self.gunList:
            if self.wave_count==gun["min_wave"]:
                self.player.guns[gun["type"]]=self.player.gun.gunData[gun["type"]]
                print("new gun unlocked!")

        for upgrade in self.player.gun.assault_upgrade:
            if self.wave_count>= upgrade["min_wave"] and upgrade not in self.upgrades:
                self.upgrades.append(upgrade)
                print("new upgrades available!")
            
            if upgrade["count"]>=upgrade["max_stack"] and upgrade  in self.upgrades:
                self.upgrades.remove(upgrade)
                print("max upgraded!")
        
        print(self.upgrades)
        choices=random.sample(self.upgrades,3)
        self.upgrade_panel=UpgradePanel()
        box=self.upgrade_panel.ids.upgrade_box
        for upgrade in choices:
            btn=Button(text=upgrade["name"],size_hint_y=None, height=60 ) 
            
            def onclick(instance,up=upgrade):
                self.apply_upgrade(up)
                self.ui_layer.remove_widget(self.upgrade_panel)
                self.game_paused=False
            btn.bind(on_press=onclick)
            box.add_widget(btn)

        self.ui_layer.add_widget(self.upgrade_panel)

    def reset(self,dt):
        self.player.gun.switch=True
        print("u can switch")

    def changeWeapeon(self):
        if not self.player.gun.switch:
            return
        self.player.gun.switch=False
        availableGuns=list(self.player.guns.keys())
        index=availableGuns.index(self.player.gun.current)
        gunindex=(index+1)%len(availableGuns)
        self.player.gun.current=availableGuns[gunindex]
        print(f"changed to {self.player.gun.current}")
        
        self.ui_layer.update()
        Clock.schedule_once(self.reset,self.player.gun.cooldown)
        



    def apply_upgrade(self,upgrade):
        type=upgrade["type"]
        value=upgrade["value"]
        target=upgrade["target"]
        upgrade["count"]+=1
        print(f'upgeaded {upgrade["count"]} times')

        if(type=="max_health"):
            self.player.max_health +=value
            self.player.healthBar.max_health +=value
            self.player.health +=value
            print(self.player.healthBar.max_health)
        elif(target=="gun"):
            gun=upgrade["gun"]
            self.player.guns[gun][type]+=value
            if(type=="reload"):
                self.player.guns[gun]["reload"] = max(0.3, self.player.guns[gun]["reload"])

            print(f"{gun} upgraded:{type}+{self.player.guns[gun][type]}")
            self.ui_layer.update()
            
        elif(target=="player"):
            if(hasattr(self.player,type)):
                setattr(self.player,type,getattr(self.player,type)+value)
        

        
        

            
    def apply_powerUp(self,power):
        if(power.type=="health"):
            self.player.health +=10
        elif(power.type=="sheild"):
            self.player.sheild=True
            Clock.schedule_once(lambda dt: setattr(self.player,"sheild",False),3)
        elif(power.type=="freeze"):
            self.player.freeze=True
            self.player.freeze_multiplier=0.3
            Clock.schedule_once(lambda dt:setattr(self.player,"freeze_multiplier",1),4)
            Clock.schedule_once(lambda dt:setattr(self.player,"freeze",False),4)
        elif(power.type=="damage_booster"):
            self.player.damage_booster=True
            self.player.damage_multiplier=1.5
            Clock.schedule_once(lambda dt:setattr(self.player,"damage_multiplier",1),5)
            Clock.schedule_once(lambda dt:setattr(self.player,"damage_booster",False),5)
        elif(power.type=="nuke"):
            for enemy in self.enemies[:]:
                enemy.health -=50
                if enemy.health <= 0:
                    if enemy not in self.remove_enemy:
                        self.remove_enemy.append(enemy)

            



    def spawnPowerUp(self,dt):
        if Window.width <= 0 or Window.height <= 0:
            return
        num=random.randint(1,5)
        powerUp=PowerUp()
        powerUp.type=self.powerUp_type[num]["type"]
        powerUp.size=(self.powerUp_type[num]["size"],self.powerUp_type[num]["size"])
        powerUp.color = self.powerUp_type[num]["color"]
        powerUp.symbol = self.powerUp_type[num]["symbol"]
        max_x=max(0,Window.width-powerUp.width)
        max_y=max(0,Window.height-powerUp.height)
        powerUp.pos=(random.uniform(0,max_x),random.uniform(0,max_y))
        self.add_widget(powerUp)
        self.powerUps.append(powerUp)
        Clock.schedule_once(lambda dt:self.despawnPowerUp(powerUp),8)

    def despawnPowerUp(self,powerUp):
        if powerUp.parent:
            self.remove_widget(powerUp)
            self.powerUps.remove(powerUp)


    def spawnAtttck(self,dt):
        if self.player.gun.reloading:
            return
        
        if self.player.guns[self.player.gun.current]["ammo"]<=0:
            return
        self.player.guns[self.player.gun.current]["ammo"]-=1
        
        
        self.ui_layer.update()
        direction=self.AttackJoystick.vector
        if direction == (0,0):
            direction = (0,1)
        attack=Attack(direction=direction)
        attack.damage=self.player.guns[self.player.gun.current]["damage"]
        attack.center=self.player.gun.center
        attack.start_x=attack.center_x
        attack.start_y=attack.center_y
        self.add_widget(attack)
        self.attacks.append(attack)
    
    def spawnEnemyAttack(self,enemy,dt):
        print("attack called")
        dx=self.player.center_x-enemy.center_x
        dy=self.player.center_y-enemy.center_y
        direction=(dx,dy)
        if direction == (0,0):
            direction = (0,1)
        Enemyattack=Attack(direction=direction)
        Enemyattack.damage=enemy.damage
        Enemyattack.center=enemy.center
        self.add_widget(Enemyattack)
        self.Enemyattacks.append(Enemyattack)

    def wave_data(self):
         self.wave_count+=1
         self.show_wave_text(self.wave_count)
         self.enemies_per_wave=4+self.wave_count*2
         print(self.enemies_per_wave)
         self.maxBoss=1+self.wave_count//2

    def spawnEnemy(self,dt):
        if self.game_paused==True:
            return
        if Window.width <= 0 or Window.height <= 0:
            return
        if self.counter==0 and len(self.enemies)==0 :
            self.show_menu()
            self.wave_data()
        self.counter +=1
        print(self.counter)

        #setting spawn for the boss wave
        if(self.counter==self.enemies_per_wave and self.bossWave==False):
            self.bossWave = True 
            self.bossAlive=self.maxBoss
            for i in range(self.maxBoss):
                self.enemy=self.spawnBoss()
            

        #setting spawn for the normal wave    
        if(self.counter<self.enemies_per_wave):
            enemy=Enemy()
            enemy.role="melee"
            enemy.boss=False
            enemy.type={ 1:{"size":30,"health":100,"speed":1,"damage":10},2:{"size":50,"health":150,"speed":0.5,"damage":20}}
            num=random.randint(1,2)
            print(num)
            print((enemy.type[num]))
            enemy.attackDelay=5
            enemy.size = (enemy.type[num]["size"],enemy.type[num]["size"])
            enemy.health=enemy.type[num]["health"]
            enemy.speed=enemy.type[num]["speed"]
            enemy.damage=enemy.type[num]["damage"]


            if(self.wave_count>0  and random.random()<0.25): #4
                enemy.role="ranged"
                enemy.minDist=150
                enemy.maxDist=220

            
            if(self.wave_count>2 and random.random()<0.15): #6
                enemy.attackDelay=2
                enemy.role="exploder"
                enemy.explode_radius=80
                enemy.explode_damage=enemy.damage*2
            
            if(self.wave_count>=2 and random.random()<0.1): #5
                enemy.role="elite"
                enemy.health *= 2
                enemy.damage *=1.5
                enemy.speed *=1.2 
            
            max_x=max(0,Window.width-enemy.width)
            enemy.pos=(random.uniform(0,max_x),Window.height)
            self.add_widget(enemy)
            print(enemy.role)
            self.enemies.append(enemy)
    
    def enemyDeath(self,enemy):
        if enemy.health <=0:
            if hasattr(enemy, "isAttack"):
                enemy.isAttack.cancel()
                del enemy.isAttack
            self.remove_widget(enemy)
            if hasattr(enemy,"healthBar"):
                self.remove_widget(enemy.healthBar)
            self.enemies.remove(enemy)
            if (self.bossWave==False):
                self.player.score +=1
            if(self.bossWave==True and enemy.boss==True):
                self.bossAlive -=1
                print(f"the bosees alive are {self.bossAlive}")
                self.player.score +=10
            if self.counter >= self.enemies_per_wave and self.bossAlive==0 and len(self.enemies)==0:
                self.bossWave=False
                self.counter=0
    
    def enemyAttack(self,enemy,dt):
        if not self.player.sheild:
            self.player.health -=enemy.damage


    def spawnBoss(self):
        if Window.width <= 0 or Window.height <= 0:
            return
        enemy=Enemy()
        enemy.role="boss"
        enemy.boss=True
        enemy.type={ 1:{"name":"boss","size":70,"health":200,"speed":1,"damage":25},2:{"name":"boss","size":70,"health":200,"speed":0.5,"damage":25}}
        num=random.randint(1,2)
        print(num)
        print((enemy.type[num]))
        enemy.size = (enemy.type[num]["size"],enemy.type[num]["size"])
        self.bossWave=True
        enemy.health=enemy.type[num]["health"]
        enemy.max_health=enemy.health
        enemy.healthBar=HealthBar(max_health=enemy.max_health,health=enemy.health)
        enemy.speed=enemy.type[num]["speed"]
        enemy.damage=enemy.type[num]["damage"]
        enemy.attackDelay=5
        max_x=max(0,Window.width-enemy.width)
        enemy.pos=(random.uniform(0,max_x),Window.height)
        self.add_widget(enemy)
        self.add_widget(enemy.healthBar)
        self.enemies.append(enemy)
    
    def show_wave_text(self,wave):
        self.wave_label=Label(
            text=f"wave:{wave}",
            font_size=40,
            size_hint=(None, None),
            size=(300, 100),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.add_widget(self.wave_label)
        Clock.schedule_once(lambda dt:self.remove_widget(self.wave_label),2)
        





    def update(self,dt):
        if self.game_paused==True:
            return
        
        

        if self.player.guns[self.player.gun.current]["ammo"]<=0 and not self.player.gun.reloading:
            print("entered")
            if hasattr(self.player, "attack"):
                self.player.attack.cancel()
                del self.player.attack
            if hasattr(self, "AttackJoystick"):
                self.AttackJoystick.shooting = False
            self.player.gun.startReload()
            

        #player
            #movement
        vx,vy=self.joystick.vector
    
        speed=4
        self.player.x +=vx*speed
        self.player.y +=vy*speed

        self.player.x=max(0,min(self.player.x,Window.width-self.player.width))
        self.player.y=max(0,min(self.player.y,Window.height-self.player.height))
        self.player.gun.update(vector=self.AttackJoystick.vector)

            #health
        self.player.healthBar.health=self.player.health
        if self.player.health <= 0:
            print("Game Over!!")

        for powers in self.powerUps:
            if powers.collide_widget(self.player):
                self.remove_powerup.append(powers)
                # self.remove_widget(powers)
                # self.powerUps.remove(powers)
                self.apply_powerUp(powers)
               
           

            #attack
        for attack in self.attacks:
            attack.x +=attack.vx*attack.speed
            attack.y +=attack.vy*attack.speed
            
            
            attack.rdx=attack.center_x-attack.start_x
            attack.rdy=attack.center_y-attack.start_y
            distance=math.hypot(attack.rdx,attack.rdy)
            if attack.y > Window.height or distance >self.player.guns[self.player.gun.current]["range"]:
                # self.remove_widget(attack)
                self.remove_attack.append(attack)
                # self.attacks.remove(attack)
            for enemy in self.enemies:
                dx=enemy.center_x-attack.center_x
                dy=enemy.center_y-attack.center_y
                radius=enemy.width*0.5

                if (dx**2+dy**2)<radius**2:
                    enemy.health -=attack.damage*self.player.damage_multiplier
                    # self.remove_widget(attack)
                    self.remove_attack.append(attack)
                    # self.attacks.remove(attack)
                    print(enemy.health)
                    if enemy.health<0:
                        if enemy not in self.remove_enemy:
                            self.remove_enemy.append(enemy)
                        # self.enemyDeath(enemy)
                    break


        for attack in self.Enemyattacks:
            attack.x +=attack.vx*attack.speed
            attack.y +=attack.vy*attack.speed
            if(attack.x<-50 or attack.x>Window.width+50 or attack.y<-50 or attack.y>Window.height+50 ):
                # self.remove_widget(attack)
                self.remove_enemyAttack.append(attack)
                # self.Enemyattacks.remove(attack)
                continue
            if attack.collide_widget(self.player):
                    self.player.health-=attack.damage
                    print(self.player.health)
                    self.remove_enemyAttack.append(attack)
                    # self.remove_widget(attack)
                    # self.Enemyattacks.remove(attack)
            
            
       
         #enemy
        for enemy in self.enemies:
            #movement
            px,py=self.player.center
            ex,ey=enemy.center
            # enemy_x=self.player.x-enemy.x
            # enemy_y=self.player.y-enemy.y
            dx=px-ex
            dy=py-ey
            enemy_distance=math.sqrt(dx**2+dy**2)
            if enemy_distance > 0:
                enemy_x =dx/(enemy_distance+0.0001)  #used for normalizing from -1 to 1 using sin and cos 
                enemy_y =dy/(enemy_distance+0.0001) 
                safe_dist=(enemy.width+self.player.width)/2
                effective_speed=enemy.speed*self.player.freeze_multiplier
                if(enemy.role !="ranged"):
                    if enemy_distance>safe_dist:
                        step = min(effective_speed, enemy_distance - safe_dist)
                        enemy.x +=enemy_x*step
                        enemy.y +=enemy_y*step
                    elif enemy_distance<safe_dist:
                        step=min(effective_speed,safe_dist-enemy_distance)
                        enemy.x -=enemy_x*step
                        enemy.y -=enemy_y*step
                if (enemy.role=="ranged"):
                    if not hasattr(enemy,"isAttack"):
                        enemy.isAttack=Clock.schedule_interval(lambda dt,e=enemy:self.spawnEnemyAttack(e,dt),enemy.attackDelay)
                    if(enemy_distance<enemy.minDist):
                        enemy.x-=enemy_x*enemy.speed
                        enemy.y-=enemy_y*enemy.speed
                    if(enemy_distance>enemy.maxDist):
                        enemy.x +=enemy_x*enemy.speed
                        enemy.y +=enemy_y*enemy.speed

            if hasattr(enemy, "healthBar"):
                enemy.healthBar.health = enemy.health
                enemy.healthBar.pos = (
                    enemy.center_x - enemy.healthBar.width / 2,
                    enemy.top + 5
                )
            


            #colloison with player
            if enemy.collide_widget(self.player):
                if enemy.role=="melee" or enemy.role=="boss":
                    if not hasattr(enemy,"isAttack"):
                        enemy.isAttack=Clock.schedule_interval(lambda dt:self.enemyAttack(enemy,dt),enemy.attackDelay)
                        print(self.player.health)
                    
                if enemy.role=="exploder":
                    self.player.health -=enemy.explode_damage
                    if hasattr(enemy, "isAttack"):
                        enemy.isAttack.cancel()
                        del enemy.isAttack
                    self.remove_enemy.append(enemy)
                    # self.remove_widget(enemy)
                    # self.enemies.remove(enemy)

            else:
                if (enemy.role == "melee" or enemy.role=="boss") and  hasattr(enemy,"isAttack"):
                    enemy.isAttack.cancel()
                    del enemy.isAttack
            
                

            #colloison with attack
            # for attack in self.attacks[:]:
            #     if enemy.collide_widget(attack):
            #             enemy.health -=attack.damage*self.player.damage_multiplier
            #             self.remove_widget(attack)
            #             self.attacks.remove(attack)
            #             print(enemy.health)
            #             if enemy.health<0:
            #                 self.enemyDeath(enemy)
        if len(self.remove_enemy)>0:
            for entity in self.remove_enemy:
                if entity in self.enemies:
                    self.enemyDeath(entity)
            self.remove_enemy.clear()
        if len(self.remove_attack)>0:
            for entity in self.remove_attack:
                if entity in self.attacks:
                    self.attacks.remove(entity)
                if entity.parent:
                    self.remove_widget(entity)
            self.remove_attack.clear()
        if len(self.remove_powerup)>0:
            for entity in self.remove_powerup:
                self.powerUps.remove(entity)
                self.remove_widget(entity)
            self.remove_powerup.clear()
        if len(self.remove_enemyAttack)>0:
            for entity in self.remove_enemyAttack:
                self.Enemyattacks.remove(entity)
                self.remove_widget(entity)
            self.remove_enemyAttack.clear()
            

                        

                



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
                
                self.parent.player.attack=Clock.schedule_interval(self.parent.spawnAtttck,self.parent.player.guns[self.parent.player.gun.current]["rate"])
                   
            return True
        
    def on_touch_up(self,touch):
            self.vector=(0,0)
            if self.shooting:
                self.parent.player.attack.cancel()
                del self.parent.player.attack
                self.shooting=False
            

            

class Gun(Widget):
    angle=NumericProperty(0)
    def __init__(self,owner,**kwargs):
        super().__init__(**kwargs)
        self.type="assualt"
        self.current="assualt"
        self.owner=owner
        self.size=(30,10)
        self.offset=(20,0)
        self.angle=0
        self.switch=True
        self.cooldown=5
        self.reloading=False
        self.gunData={
                "assualt":{"damage": 25,"range": 800,"magazine": 30,"ammo":30,"rate": 0.5,"reload": 1.5},
                "sniper":{"damage": 50,"range": 1400,"magazine": 7,"ammo":7,"rate": 1.2,"reload": 2.5},
                "shotgun":{"damage": 30,"range": 350,"magazine": 2,"ammo":2,"rate": 0.9,"reload": 2.0},
                "machine":{"damage": 20,"range": 700,"magazine": 25,"ammo":25,"rate": 0.15,"reload": 2.2}
        }
        self.assault_upgrade= [
    # 
    {
    "target":"gun",
    "gun":"assualt",
    "name":"Assault Damage++",
    "type":"damage",
    "value":5,
    "min_wave":1,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"assualt",
    "name":"Assault Extended Magazine",
    "type":"magazine",
    "value":4,
    "min_wave":1,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"assualt",
    "name":"Assault Fast Reload",
    "type":"reload",
    "value":-0.15,
    "min_wave":2,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"assualt",
    "name":"Assault Extended Barrel",
    "type":"range",
    "value":60,
    "min_wave":2,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"sniper",
    "name":"Sniper Damage++",
    "type":"damage",
    "value":12,
    "min_wave":2,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"shotgun",
    "name":"Shotgun Damage++",
    "type":"damage",
    "value":8,
    "min_wave":1,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"shotgun",
    "name":"Shotgun Extended Shell",
    "type":"magazine",
    "value":1,
    "min_wave":1,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"shotgun",
    "name":"Shotgun Quick Pump",
    "type":"reload",
    "value":-0.2,
    "min_wave":2,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"shotgun",
    "name":"Shotgun Choke Barrel",
    "type":"range",
    "value":40,
    "min_wave":2,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"sniper",
    "name":"Sniper Extended Magazine",
    "type":"magazine",
    "value":1,
    "min_wave":2,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"sniper",
    "name":"Sniper Fast Reload",
    "type":"reload",
    "value":-0.25,
    "min_wave":3,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"sniper",
    "name":"Sniper Precision Barrel",
    "type":"range",
    "value":120,
    "min_wave":3,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"sniper",
    "name":"Sniper Damage++",
    "type":"damage",
    "value":12,
    "min_wave":2,
    "max_stack":2,
    "count":0
},

{
    "target":"gun",
    "gun":"machine",
    "name":"Machine Damage++",
    "type":"damage",
    "value":3,
    "min_wave":1,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"machine",
    "name":"Machine Extended Magazine",
    "type":"magazine",
    "value":6,
    "min_wave":1,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"machine",
    "name":"Machine Fast Reload",
    "type":"reload",
    "value":-0.18,
    "min_wave":2,
    "max_stack":2,
    "count":0
},
{
    "target":"gun",
    "gun":"machine",
    "name":"Machine Reinforced Barrel",
    "type":"range",
    "value":50,
    "min_wave":2,
    "max_stack":2,
    "count":0
},

]
    def reload(self,dt):
        self.reloading=False
        self.parent.player.guns[self.parent.player.gun.current]["ammo"]=self.parent.player.guns[self.parent.player.gun.current]["magazine"]
        self.parent.ui_layer.update()
    def startReload(self):
        if self.reloading :
            return
        self.reloading=True
        Clock.schedule_once(self.parent.player.gun.reload,self.parent.player.guns[self.parent.player.gun.current]["reload"])
        
    def update(self,vector):
        self.center=self.owner.center
        dx,dy=vector
        length=math.sqrt(dx**2+dy**2)
        if dx==0 and dy==0:
            return
        self.angle=math.degrees(math.atan2(dy,dx))
        dx /=length
        dy /=length
        self.center_x=self.owner.center_x+dx*self.offset[0]
        self.center_y=self.owner.center_y+dy*self.offset[1]




class PowerUp(Widget):
    color=ListProperty([1,1,1,1])
    symbol=StringProperty("")


class Player(Widget):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.damage=200
        self.health=100
        self.max_health=100
        self.sheild=False
        self.damage_multiplier=1
        self.score=0
        self.freeze_multiplier=1
        self.regen=0
        

class Enemy(Widget):
    pass

class HealthBar(Widget):
    health=NumericProperty(100)
    max_health=NumericProperty(100)

class Attack(Widget):
    def __init__(self,direction=(0,1),**kwargs):
        super().__init__(**kwargs)
        self.size = (12, 12)
        dx,dy=direction
        length=math.sqrt(dx**2+dy**2)
        if length ==0:
            self.vx,self.vy=0,1
        else:
            self.vx =dx/length
            self.vy =dy/length
        self.start_x=0
        self.start_y=0
        self.speed=7
        self.damage=50

class GameUI(RelativeLayout):
    ammo_ratio=NumericProperty(1)
    def __init__(self,**kwargs):
            super().__init__(**kwargs)
    def update(self):
        gun=self.parent.player.guns[self.parent.player.gun.current]
        self.ids.gun_text.text = (
        f"{self.parent.player.gun.current} "
        f"{gun['ammo']}/{gun['magazine']}")
        self.ammo_ratio=gun["ammo"]/gun["magazine"]

class UpgradePanel(RelativeLayout):
    pass


class Escape(App):
    def build(self):
        return Game()
if __name__ == '__main__':
    Escape().run()