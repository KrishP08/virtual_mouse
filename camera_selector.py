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
        self.camera_tree.bind('<<TreeviewSelect>>',self.on_camera_select)

        #Handle window closing
        self.selected_window.protocol("WM_DELETE_WINDOW",self.cancel_selection)

        #Center the window
        self.selected_window.update_idletasks()
        width=self.selected_window.winfo_width()
        height=self.selected_window.winfo_height()
        x=(self.selected_window.winfo_screenmmwidth()//2)-(width//2)
        y=(self.selected_window.winfo_screenheight()//2)-(height//2)
        self.selected_window.geometry(f'{width}x{height}+{x}+{y}')

        # Wait for selection
        self.selected_window.wait_window()

        return self.selected_camera
    def on_camera_select(self,event):
        """Handle camera selection change"""
        selection=self.camera_tree.selection()
        if selection:
            item=self.camera_tree.item(selection[0])
            camera_name=item['values'][0]
            # Find camera index by name
            for camera in self.available_cameras:
                if camera['name']==camera_name:
                    self.selected_camera=camera['index']
                    break
    
    def refresh_cameras(self):
        """Refresh the camera list"""
        # Stop preview if running
        if self.preview_running:
            self.toggle_preview()

        # Clear existing items
        for item in self.camera_tree.get_children():
            self.camera_tree.delete(item)

        # Detect cameras again
        self.detect_cameras()

        # Add cameras to the tree
        for camera in self.available_cameras:
            self.camera_tree.insert(',"end',values=(
                camera['name'],
                camera['resolution'],
                camera['fps'],
                camera['backend']
            ))

        # Select first camera by default
        if self.available_cameras:
            self.camera_tree.selection_set(self.camera_tree.get_children()[0])
            self.selected_camera=self.available_cameras[0]['index']
    
    def toggle_preview(self):
        """Toggle camera preview"""
        if self.preview_running:
            self.stop_preview()
        else:
            self.start_preview()
    
    def start_preview(self):
        """Start camera preview"""
        if self.preview_running:
            return
        
        self.preview_running=True
        self.preview_btn.config(text="Stop preview")

        # Start preview in separate thread
        self.preview_thread=threading.Thread(target=self.preview_loop,daemon=True)
        self.preview_thread.start()

    def stop_preview(self):
        """Stop camera preview"""
        self.preview_running=False
        self.preview_btn.config(text="Preview Selected Camera")

        if self.preview_cap:
            self.preview_cap.release()
            self.preview_cap=None
        
        cv2.destroyAllWindows()

    def preview_loop(self):
        """Camera preview loop"""
        self.preview_cap=cv2.VideoCapture(self.selected_camera)

        if not self.preview_cap.isOpened():
            messagebox.showerror("Error",f"Cannot open camera {self.selected_camera}")
            self.preview_running=False
            self.preview_btn.config(text="Preview Selected Camera")
            return

        window_name=f"Camera {self.selected_camera} Preview - Press 'q' to close"
        cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name,640,480)

        while self.preview_running:
            ret,frame =self.preview_cap.read()
            if not ret:
                break

            # Add preview text
            cv2.putText(frame,f"Camera {self.selected_camera} Preview",(10,30),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
            cv2.putText(frame,"Press 'q' to close preview",(10,60),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2)
            
            cv2.imshow(window_name,frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.preview_cap.release()
        cv2.destroyWindow(window_name)
        self.preview_running=False

        # Update button text on main thread
        try:
            self.preview_btn.config(text="Preview Selected Camera")
        except:
            pass #Window might be closed

    def select_camera(self,callback):
        """Select the camera and close dialog"""
        # Stop preview if running
        if self.preview_running:
            self.stop_preview()

        if callback:
            callback(self.selected_camera)

        self.selector_window.destroy()

    def cancel_selection(self):
        """Cancel camera selection"""
        # Stop preview if running
        if self.preview_running:
            self.stop_preview()

        self.selected_camera=None
        self.selected_window.destroy()
def show_camera_selector():
    """Standalong function to show camera selector"""
    root=tk.Tk()
    root.withdraw()

    selector=CameraSelector()
    selected_camera=selector.show_camera_selector()

    root.destroy()
    return selected_camera

if __name__=="__main__":
    #Test the camera selector
    selected = show_camera_selector()
    if selected is not None:
        print(f"Selected camera: {selected}")
    else:
        print("No camera selected")
