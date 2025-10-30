import os
import uuid
from werkzeug.utils import secure_filename
from flask import send_file, abort
import mimetypes
# from moviepy.editor import VideoFileClip
import os
import cv2

class FileService:
    def __init__(self):
        self.upload_folder = os.environ.get('UPLOAD_FOLDER', 'uploads')
        self.max_file_size = 16 * 1024 * 1024  # 16MB
        
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def save_file(self, file, subfolder=None):
        """Save uploaded file and return file path and size"""
        try:
            if not file or not file.filename:
                raise ValueError("No file provided")
            
            # Check file size (if available)
            if hasattr(file, 'content_length') and file.content_length:
                if file.content_length > self.max_file_size:
                    raise ValueError(f"File size exceeds maximum allowed size of {self.max_file_size // (1024*1024)}MB")
            
            # Secure the filename
            filename = secure_filename(file.filename)
            if not filename:
                raise ValueError("Invalid filename")
            
            # Generate unique filename to avoid conflicts
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
            
            # Create subfolder if specified
            if subfolder:
                folder_path = os.path.join(self.upload_folder, subfolder)
                os.makedirs(folder_path, exist_ok=True)
                file_path = os.path.join(folder_path, unique_filename)
                relative_path = os.path.join(subfolder, unique_filename)
            else:
                file_path = os.path.join(self.upload_folder, unique_filename)
                relative_path = unique_filename
            
            # Save the file
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            return relative_path, file_size
            
        except Exception as e:
            raise Exception(f"File save error: {str(e)}")
    
    def delete_file(self, file_path):
        """Delete file from filesystem"""
        try:
            if not file_path:
                return False
            
            # Construct full path
            if not os.path.isabs(file_path):
                full_path = os.path.join(self.upload_folder, file_path)
            else:
                full_path = file_path
            
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False
    
    def send_file(self, file_path, download_name=None):
        """Send file for download"""
        try:
            print("file path recieved to file service",file_path)

            if not file_path:
                abort(404, "File not found")
            
            # # Construct full path
            # if not os.path.isabs(file_path):
            #     full_path = os.path.join(self.upload_folder, file_path)
            # else:
            #     full_path = file_path
            #     full_path = file_path.replace("\\", "/")
            full_path = file_path
            if not os.path.exists(full_path):
                abort(404, "File not found")
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(full_path)
            
            return send_file(
                full_path,
                as_attachment=True,
                download_name=download_name or os.path.basename(full_path),
                mimetype=mime_type
            )
            
        except Exception as e:
            abort(500, f"Error serving file: {str(e)}")
    
    def get_file_info(self, file_path):
        """Get file information"""
        try:
            if not file_path:
                return None
            
            # Construct full path
            if not os.path.isabs(file_path):
                full_path = os.path.join(self.upload_folder, file_path)
            else:
                full_path = file_path
            
            if not os.path.exists(full_path):
                return None
            
            stat_info = os.stat(full_path)
            mime_type, _ = mimetypes.guess_type(full_path)
            
            return {
                'path': file_path,
                'size': stat_info.st_size,
                'modified': stat_info.st_mtime,
                'mime_type': mime_type,
                'filename': os.path.basename(full_path)
            }
            
        except Exception as e:
            print(f"Error getting file info for {file_path}: {str(e)}")
            return None
    
    def validate_file_type(self, filename, allowed_extensions):
        """Validate if file type is allowed"""
        if not filename:
            return False
        
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in allowed_extensions
    
    def get_file_extension(self, filename):
        """Get file extension"""
        if not filename or '.' not in filename:
            return None
        
        return filename.rsplit('.', 1)[1].lower()
    
    def create_directory(self, path):
        """Create directory if it doesn't exist"""
        try:
            full_path = os.path.join(self.upload_folder, path)
            os.makedirs(full_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {path}: {str(e)}")
            return False
    
    def list_files(self, subfolder=None):
        """List files in upload directory or subfolder"""
        try:
            if subfolder:
                folder_path = os.path.join(self.upload_folder, subfolder)
            else:
                folder_path = self.upload_folder
            
            if not os.path.exists(folder_path):
                return []
            
            files = []
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    stat_info = os.stat(file_path)
                    mime_type, _ = mimetypes.guess_type(file_path)
                    
                    relative_path = os.path.join(subfolder, filename) if subfolder else filename
                    
                    files.append({
                        'filename': filename,
                        'path': relative_path,
                        'size': stat_info.st_size,
                        'modified': stat_info.st_mtime,
                        'mime_type': mime_type
                    })
            
            return files
            
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []
    
    def get_upload_stats(self):
        """Get upload statistics"""
        try:
            total_files = 0
            total_size = 0
            
            for root, dirs, files in os.walk(self.upload_folder):
                total_files += len(files)
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'total_size_mb': total_size / (1024 * 1024)
            }
            
        except Exception as e:
            print(f"Error getting upload stats: {str(e)}")
            return {
                'total_files': 0,
                'total_size': 0,
                'total_size_mb': 0
            }
    
    def cleanup_old_files(self, days=30):
        """Clean up files older than specified days"""
        try:
            import time
            
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            
            deleted_count = 0
            deleted_size = 0
            
            for root, dirs, files in os.walk(self.upload_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        stat_info = os.stat(file_path)
                        if stat_info.st_mtime < cutoff_time:
                            file_size = stat_info.st_size
                            os.remove(file_path)
                            deleted_count += 1
                            deleted_size += file_size
                    except OSError:
                        continue
            
            return {
                'deleted_files': deleted_count,
                'deleted_size': deleted_size,
                'deleted_size_mb': deleted_size / (1024 * 1024)
            }
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            return {
                'deleted_files': 0,
                'deleted_size': 0,
                'deleted_size_mb': 0
            }
    

    def get_video_duration_minutes(file_path):
        cap = cv2.VideoCapture(file_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        if fps > 0:
            duration_seconds = frame_count / fps
            return round(duration_seconds / 60, 2)
        return None
        