import OpenGL.GL as gl 
import OpenGL.GLU as glu 
import OpenGL.GLUT as glut 
from OpenGL.arrays import vbo
from laspy.file import File
import numpy as np
import random
import sys

def run_glviewer(file_object, mode, dim):
    glviewer = pcl_image(file_object, mode, dim)
    return(0)

class VBO_Provider():
    def __init__(self, file_object, vbsize, means, mode, dim):
        self.vbos = []
        self.allcolor = False
        start_idx = 0
        self.file_object = file_object
        end_idx = vbsize
        i = 1

        while(start_idx < len((file_object))):
            i += 1
            try:
                end_idx = min(len(file_object), start_idx + vbsize) 
                print("Buffering points " + str(start_idx) + " to " + str((end_idx)))
                dat = self.slice_file(start_idx, end_idx, means)
                self.set_color_mode(mode,dim, start_idx, end_idx, dat)
                _vbo = vbo.VBO(data = np.array(dat, dtype = np.float32),
                            usage = gl.GL_DYNAMIC_DRAW, target = gl.GL_ARRAY_BUFFER)
                self.vbos.append((_vbo, end_idx -start_idx))
                start_idx += vbsize
            except Exception, err:
                print("Error initializing VBO:")
                print(err)


    def slice_file(self,start_idx, end_idx, means):
        return(np.array(np.vstack((self.file_object.x[start_idx:end_idx], self.file_object.y[start_idx:end_idx], self.file_object.z[start_idx:end_idx], 
                                  np.zeros(end_idx - start_idx),np.zeros(end_idx - start_idx),np.zeros(end_idx - start_idx))).T) - means)

    def bind(self):
        for _vbo in self.vbos:
            _vbo[0].bind()

    def unbind(self):
        for _vbo in self.vbos:
            _vbo[0].unbind()
    def draw(self):

        for _vbo in self.vbos:
            _vbo[0].bind()
            gl.glVertexPointer(3, gl.GL_FLOAT, 24,_vbo[0])
            gl.glColorPointer(3, gl.GL_FLOAT, 24, _vbo[0] + 12)
            gl.glDrawArrays(gl.GL_POINTS, 0, _vbo[1]) 
            _vbo[0].unbind()
        #gl.glMultiDrawArrays(gl.GL_POINTS, 0,100000, len(self.vbos))
    
    def set_color_mode(self, mode, dim,start_idx, end_idx, data): 
        if mode in ["grey", "greyscale", "intensity"]:
            if type(self.allcolor) == bool:
                self.allcolor = self.file_object.reader.get_dimension(dim)/float(np.max(self.file_object.get_dimension(dim)))
            scaled = self.allcolor[start_idx:end_idx] + 0.1
            col = np.array((np.vstack((scaled, scaled, scaled)).T), dtype = np.float32)
            data[:,3:6] += col
            return(data)
        elif (mode == "elevation" or (mode == "heatmap" and dim == "z")):
            if type(self.allcolor) == bool:
                self.allcolor = self.heatmap(self.file_object.z)
            col = self.allcolor[start_idx:end_idx]
            data[:,3:6] += col
            return(data)
        elif (mode == "heatmap" and dim != "z"):
            if type(self.allcolor) == bool:
                self.allcolor = self.heatmap(self.file_object.reader.get_dimension(dim))
            col = self.allcolor[start_idx:end_idx]
            data[:,3:6] += col
            return(data)
        elif mode == "rgb":
            _max = max(np.max(self.file_object.red), np.max(self.file_object.green), np.max(self.file_object.blue))
            _min = min(np.min(self.file_object.red), np.min(self.file_object.green), np.min(self.file_object.blue))
            diff = _max - _min
            col = np.array(np.vstack((self.file_object.red[start_idx:end_idx], self.file_object.green[start_idx:end_idx], self.file_object.blue[start_idx:end_idx])).T, dtype = np.float32)
            col -= _min
            col /= diff
            data[:,3:6] += col
            return(data)

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

class pcl_image():
    def __init__(self, file_object, mode, dim):
        self.file_object = file_object
        self.read_data(mode, dim)
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
 
    def read_data(self, mode, dim):
        means = np.array([np.mean(self.file_object.x, dtype = np.float64), 
                          np.mean(self.file_object.y, dtype = np.float64), 
                          np.mean(self.file_object.z, dtype = np.float64),
                          0,0,0])
        
        self.N = len(self.file_object)
        self.data_buffer = VBO_Provider(self.file_object, 1000000, means, mode, dim) 

 

    def reshape(self, w, h):
        print("Reshape " + str(w) + ", " + str(h))
        ratio = w if h == 0 else float(w)/h
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glViewport(0,0,w,h)
        gl.glLoadIdentity()
        glu.gluPerspective(90,float(ratio),1,2000);

        gl.glMatrixMode(gl.GL_MODELVIEW)
        
    def timerEvent(self, arg):
        # Do stuff
        glut.glutPostRedisplay()
        glut.glutTimerFunc(10,self.timerEvent,1)

    def draw_points(self, num):

        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)
        self.data_buffer.draw()

        gl.glDisableClientState(gl.GL_COLOR_ARRAY)
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
         
        
            
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
            self.look_granularity /= 0.8
        elif key == "-":
            self.movement_granularity /= 0.8
            self.look_granularity *= 0.8
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

