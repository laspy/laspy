import OpenGL.GL as gl 
import OpenGL.GLU as glu 
import OpenGL.GLUT as glut 
from OpenGL.arrays import vbo
from laspy.file import File
import numpy as np
import random
import sys

def run_glviewer(file_object, mode):
    glviewer = pcl_image(file_object, mode)
    return(0)

class VBO_Provider():
    def __init__(self, array, vbsize):
        self.vbos = []
        start_idx = 0
        end_idx = vbsize
        i = 1
        while(start_idx < array.shape[0]):
            print("Adding Data Buffer " + str(i))
            i += 1
            try:
                st_index = start_idx
                end_idx = min(array.shape[0], start_idx + vbsize) 
                _vbo = vbo.VBO(data = array[start_idx:end_idx,:],
                            usage = gl.GL_DYNAMIC_DRAW, target = gl.GL_ARRAY_BUFFER)
                self.vbos.append((_vbo, end_idx -start_idx))
                start_idx += vbsize
            except Exception, err:
                print("Error initializing VBO:")
                print(err)
            print(self.vbos[-1][1])
    def bind(self):
        for _vbo in self.vbos:
            _vbo[0].bind()

    def unbind(self):
        for _vbo in self.vbos:
            _vbo[0].unbind()
    def draw(self):
        i =0
        for _vbo in self.vbos:
            gl.glVertexPointer(3, gl.GL_FLOAT, 24,_vbo[0])
            gl.glColorPointer(3, gl.GL_FLOAT, 24, _vbo[0] + 12)
            i += vbo[1]
        gl.glDrawArrays(gl.GL_POINTS,0,_i)





class pcl_image():
    def __init__(self, file_object, mode = 3):
        self.file_object = file_object
        self.read_data(mode)
        self.movement_granularity = 1.0
        self.look_granularity = 16.0
        self.main()

    def main(self): 
        self.location = np.array([0.0,0.0,1500.0])
        self.focus = np.array([0.0,0.0,0.0])
        self.up = np.array([1.0,0.0,0.0])

        self.mousex = 0
        self.mousey = 0
        self.mouse_drag = gl.GL_FALSE

        # Wire up GL
        #gl.glPointSize(4)
        glut.glutInit(sys.argv)

        glut.glutInitDisplayMode(glut.GLUT_RGB | glut.GLUT_DOUBLE | glut.GLUT_DEPTH)
        glut.glutInitWindowSize(500,500)
        glut.glutInitWindowPosition(10,10)
        glut.glutCreateWindow("Laspy+OpenGL Pointcloud")
        glut.glutDisplayFunc(self.display)
        glut.glutReshapeFunc(self.reshape)
        glut.glutMouseFunc(self.mouse)
        glut.glutMotionFunc(self.mouse_motion)
        glut.glutKeyboardFunc(self.keyboard)
        gl.glClearColor(0.0,0.0,0.0,1.0)
        glut.glutTimerFunc(10,self.timerEvent,1)

        glut.glutMainLoop()
        return 0
        

    def read_data(self, mode):
        data = np.array(np.vstack((self.file_object.x, self.file_object.y, self.file_object.z, 
                    np.zeros(len(self.file_object)),np.zeros(len(self.file_object)),
                    np.zeros(len(self.file_object)))).T)
        #data = np.array(np.vstack((self.file_object.x, self.file_object.y, self.file_object.z)).T ,dtype=np.float32)
        means = np.mean(data, axis = 0, dtype = np.float64)
        tmp = data - means
        self.data = np.array((tmp),dtype = np.float32)
        self.N = len(self.file_object)
        try:
            print("Generating Color Matrix")
            self.set_color_mode(mode)
        except:
            print("Error using color mode: " +str(mode) + ", using mode 3.")
            self.set_color_mode(2)
        self.data_buffer = VBO_Provider(self.data, 100000)
        #self.data_buffer = vbo.VBO(data = self.data,usage= gl.GL_DYNAMIC_DRAW, target = gl.GL_ARRAY_BUFFER)

 
    def set_color_mode(self, mode):
        if mode == 1:
            col = np.array([0,0,0,1,1,1], dtype = np.float32)
            self.data = self.data+ col 
        elif mode == 2:
            scaled = self.file_object.intensity/float(np.max(self.file_object.intensity))
            col = np.array(np.vstack((np.zeros(self.N), np.zeros(self.N), np.zeros(self.N), 
                            scaled + 0.1, scaled + 0.1, scaled + 0.1)).T, dtype = np.float32)
            self.data = np.sum([self.data, col], axis = 0)

        elif mode == 3:
            print("Mode3")
            col = self.heatmap(self.data[:,2])
            self.data[:,3:6] += col
        elif mode == 4:
            _max = max(np.max(self.file_object.red), np.max(self.file_object.green), np.max(self.file_object.blue))
            _min = min(np.min(self.file_object.red), np.min(self.file_object.green), np.min(self.file_object.blue))
            diff = _max - _min
            col = np.array(np.vstack((self.file_object.red, self.file_object.green, self.file_object.blue)).T, dtype = np.float32)
            col -= _min
            col /= diff
            self.data[:,3:6] += col

    def heatmap(self, vec, mode = 1):
        _max = np.max(vec)
        _min = np.min(vec)
        diff = _max-_min
        red = (vec-_min)/float(diff) 
        if mode == 1:
            col = np.array(np.vstack((red**4, np.sqrt(0.0625-(0.5-red)**4) , (1-red)**4)),dtype = np.float32).T 
        else:
            col = np.array(np.vstack((red**4, np.zeros(self.N) , (1-red)**4)),dtype = np.float32).T 


        return(col)

    def reshape(self, w, h):
        print("Reshape " + str(w) + ", " + str(h))
        ratio = w if h == 0 else float(w)/h
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glViewport(0,0,w,h)
        gl.glLoadIdentity()
        glu.gluPerspective(90,float(ratio),1,2000);
        #glu.gluPerspective(359,float(ratio),1,100000)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        
    def timerEvent(self, arg):
        # Do stuff
        glut.glutPostRedisplay()
        glut.glutTimerFunc(10,self.timerEvent,1)

    def draw_points(self, num):
        self.data_buffer.bind()        
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)
        self.data_buffer.draw()

        #gl.glDrawElementsui(0,num)

        self.data_buffer.unbind()
        gl.glDisableClientState(gl.GL_COLOR_ARRAY)
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        



        
        #buff.bind_vertexes(3, gl.GL_FLOAT)
        #gl.glDrawElementsui(gl.GL_POINTS, range(num))
        
            
    def rotate_vector(self, vec_rot, vec_about, theta):
        d = np.sqrt(vec_about.dot(vec_about))
        
        L = np.array((0,vec_about[2], -vec_about[1], 
                    -vec_about[2], 0, vec_about[0],
                    vec_about[1], -vec_about[0], 0))
        L.shape = (3,3)

        
        try:
           R = (np.identity(3) + np.sin(theta)/d*L +
                    (1-np.cos(theta))/(d*d)*(L.dot(L)))
        except:
            print("Error in rotation.")
            return()
        return(vec_rot.dot(R))

    def display(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()
        glu.gluLookAt(self.location[0], self.location[1], self.location[2], 
                      self.focus[0],self.focus[1], self.focus[2] ,
                      self.up[0], self.up[1], self.up[2])
        self.draw_points(self.N)
        glut.glutSwapBuffers()

    def camera_move(self,ammount, axis = 1):
        if axis == 1:
            pointing = self.focus - self.location
            pnorm = np.sqrt(pointing.dot(pointing))
            pointing /= pnorm
            self.location = self.location + ammount*pointing
            self.focus = self.location + pnorm*pointing
        elif axis == 2:
            pointing = self.focus - self.location
            direction = np.cross(self.up, pointing)
            direction /= np.sqrt(direction.dot(direction))
            self.location = self.location + ammount * direction
            self.focus = self.location + pointing
            
    def camera_yaw(self, theta):
        pointing = self.focus - self.location
        newpointing = self.rotate_vector(pointing, self.up, theta)
        self.focus = newpointing + self.location

    def camera_roll(self, theta):
        self.up = self.rotate_vector(self.up, self.focus-self.location, theta)

    def camera_pitch(self,theta):
        pointing = self.focus - self.location
        axis = np.cross(self.up, pointing)
        newpointing = self.rotate_vector(pointing, axis, theta)
        self.focus = newpointing + self.location
        self.up = np.cross(newpointing, axis)
        self.up /= np.sqrt(self.up.dot(self.up))

    def mouse(self, button, state, x, y):
        if button == glut.GLUT_LEFT_BUTTON:
            if state == glut.GLUT_DOWN:
                self.mouse_drag = gl.GL_TRUE
                self.mousex = x
                self.mousey = y
            elif state == glut.GLUT_UP and self.mouse_drag:
                self.mouse_drag = gl.GL_FALSE
        elif button == 3:
            #Scoll up
            pass
        elif button == 4:
            #Scroll down
            pass

    def mouse_motion(self,x,y):
        if self.mouse_drag:
            self.mousex = x
            self.mousey = y

    def keyboard(self,key, x, y):
        ## Looking
        if key == "a":
            self.camera_yaw(np.pi/(self.look_granularity))
        elif key == "d":
            self.camera_yaw(-np.pi/self.look_granularity)
        elif key == "w":
            self.camera_pitch(-np.pi/self.look_granularity)
        elif key == "s":
            self.camera_pitch(np.pi/self.look_granularity)
        elif key == "e":
            self.camera_roll(np.pi/self.look_granularity)
        elif key == "q":
            self.camera_roll(-np.pi/self.look_granularity)
        ## Moving
        elif key == "W":
            self.camera_move(self.movement_granularity * 100.0)
        elif key == "S":
            self.camera_move(self.movement_granularity *-100.0)
        elif key == "A":
            self.camera_move(self.movement_granularity * 100.0, axis = 2)
        elif key == "D":
            self.camera_move(self.movement_granularity * -100.0, axis = 2)
        elif key == "+":
            self.movement_granularity *= 0.8
            self.look_granularity = min(self.look_granularity + 1, 50)
        elif key == "-":
            self.movement_granularity /= 0.8
            self.look_granularity = max(self.look_granularity - 1, 8)
        elif key in ("x", "y", "z"):
            self.set_up_axis(key)
        print(key)
        pass

    def set_up_axis(self, key):
        if key == "x":
            self.up = np.array([1.0, 0.0001, 0.0001])
            self.focus[0] = self.location[0]
        elif key == "y":
            self.up = np.array([0.0001, 1.0, 0.0001])
            self.focus[1] = self.location[1]
        elif key == "z":
            self.up = np.array([0.0001, 0.0001, 1.0])
            self.focus[2] = self.location[2]
        if all(self.focus == self.location):
            self.focus[{"x":1, "y":2, "z":0}[key]] += 1500

