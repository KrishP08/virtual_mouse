import cv2
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class CameraSelector:
    def __init__(self):
        self.available_cameras=[]
        self.selected_camera=0
        self.preview_running=False
        self.preview_cap=None

    def detect_cameras(self,max_cameras=10):
        """Detect available cameras on the system"""
        self.available_cameras=[]

        for i in range(max_cameras):
            cap=cv2.VideoCapture(i)
            if cap.isOpened():
                # try to read a frame to verify the camera works
                ret,frame=cap.read()
                if ret:
                    # Get camera properties
                    width =int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps=int(cap.get(cv2.CAP_PROP_FPS))

                    camera_info={
                        'index':i,
                        'name':f"Camera {i}",
                        'resolution': f"{width}x{height}",
                        'fps':fps
                    }

                    #try to get more detialled camera info
                    try:
                        backend=cap.getBackendName()
                        camera_info['backend']=backend
                    except:
                        camera_info['backend']="Unknowm"

                    self.available_cameras.appernd(camera_info)

                cap.release()
            else:
                cap.release()
        return self.available_cameras
    
    def show_camera_selector(self,callback=None):
        """Show camera selection dialog"""
        if not self.available_cameras:
            self.detect_cameras()

        if not self.available_cameras:
            messagebox.showerror("Error","No cameras detected on your system!")
            return None

        if len(self.available_cameras)==1:
            #Only one camera,return it directly
            if callback:
                callback(0)
            return 0
        
        #Multiple cameras,show selection dialog
        self.selected_window=tk.Toplevel()
        self.selected_window.title("Select Camera")
        self.selected_window.geometry("600x400")
        self.selected_window.configure(bg='#2b2b2b')
        self.selected_window.attributes('-topmost',True)

        #Make it modal
        self.selector_window.grab_set()

        #Title 
        title_label=tk.Label(self.selected_window,text="Choose Camera",bh='#2b2b2b',fg='white',font=('Arial',16,'bold'))
        title_label.pack(pady=10)

        #Camera list frame
        list_frame=tk.Frame(self.selected_window,bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH,expand=True,padx=20,pady=10)

        #Create treeview fro camera list
        columns=('Camera','Resolution','FPS','Backend')
        self.camera_tree=ttk.Treeview(list_frame,columns=columns,show='headings',height=8)

        #Configure column headings
        self.camera_tree.heading('Camera',text='Camera')
        self.camera_tree.heading('Resolution',text='Resolution')
        self.camera_tree.heading('FPS',text='FPS')
        self.camera_tree.heading('Backend',text='Backend')

        #Configure column widths
        self.camera_tree.column('Camera',width=150)
        self.camera_tree.column('Resolution',width=120)
        self.camera_tree.column('FPS',width=80)
        self.camera_tree.column('Backend',width=120)

        #Add cameras to the tree
        for camera in self.available_cameras:
            self.camera_tree.insert('','end',values=(
                camera['name'],
                camera['resolution'],
                camera['fps'],
                camera['backend']
            ))

        # Select first camera by default
        if self.available_cameras:
            self.camera_tree.selection_set(self.camera_tree.get_children()[0])

        self.camera_tree.pack(fill=tk.BOTH,expand=True)

        #Preview frame
        preview_frame=tk.Frame(self.selected_window, bg='#2b2b2b')
        preview_frame.pack(fil=tk.X,padx=20,pady=10)

        #Preview button
        self.preview_btn= tk.Button(preview_frame,text="Preview Selected Camera",command=self.toggle_preview,bg='#404040',fg='white',font=('Arial',10))
        self.preview_btn.pack(side=tk.LEFT,padx=5)

        # Refresh button
        refresh_btn=tk.Button(preview_frame,text="Refresh Camera List",command=self.refresh_cameras,bg='#404040',fg='white',font=('Arial',10))
        refresh_btn.pack(side=tk.LEFT,padx=5)

        # Button frame
        button_frame=tk.Frame(self.selected_window,bg='#2b2b2b')
        button_frame.pack(pady=20)

        #Select button
        select_btn=tk.Button(button_frame,text="Select Camera",command=lambda:self.selected_camera(callback),bg='#006600',fg='white',font=('Arial',12),width=15)
        select_btn.pack(side=tk.LEFT,padx=10)

        #Cancel button
        cancel_btn=tk.Button(button_frame,text="Cancel",command=self.cancel_selection,bg='#660000',fg='white',font=('Arial',12),width=15)

        cancel_btn.pack(side=tk.LEFT,padx=10)

        #Bind selection change
        