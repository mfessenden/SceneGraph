#!/X/tools/binlinux/xpython
import os
import simplejson as json
from . import logger



class RecentFiles(object):
    """
    TODO:
        - implement max items functions
    
    """
    def __init__(self, parent=None, **kwargs):
        
        self._ui                = kwargs.get('ui', 'SceneGraph')
        self.__parent           = parent
        self.__package_path     = os.path.dirname(__file__)
        self.__package          = os.path.split(os.path.dirname(__file__))[-1]
        self.__prefsdir         = os.path.join(os.getenv('HOME'), '.mrx', self.__package)
        self.__prefsfile        = kwargs.get('filename', os.path.join(self.__prefsdir, 'recent_files.json'))
        self.__backupprefs      = '%s-BAK' % self.__prefsfile
        self.__qtsettings       = os.path.join(self.prefsdir, '%s.ini' % self._ui)
        self.__max_items        = kwargs.get('max', 10)
        
        self.initializeData()
        
        if not os.path.exists(self.prefsfile):
            self.write()
        else:
            self.read()

    def initializeData(self):
        """ 
        initialize the data structure 
        """
        logger.getLogger().debug('initializing %s prefs data' % self.__package)
        self.__data = dict()
        recent_files = dict()
        self.__data.update(recent_files=recent_files)
    
    def addFile(self, filename):
        if filename not in self.getRecentFiles():            
            current_index = self.getLatestFileIndex()
            ci = str(current_index)
            self.data.get('recent_files').update({ci:filename})
            self.write()        
    
    def removeOldestIndex(self):
        new_data = dict()
        self.data.get('recent_files').pop('0')
        for idx in sorted(self.data.get('recent_files').keys()):
            nidx = str(int(idx)-1)
            new_data[nidx] = self.data.get('recent_files').get(idx)
        self.data['recent_files'] = new_data
    
    def getRecentFiles(self):
        """
        Returns a tuple of recent files, by order in which they were added
        """
        files = []
        if self.data.get('recent_files'):
            for idx in sorted(self.data.get('recent_files').keys()):
                files += (self.data.get('recent_files').get(idx),)
        files.reverse()
        files = tuple(files)
        return files
    
    def getLatestFileIndex(self):
        """
        Returns an index of the last file added
        
        returns:
            (int)  - index of the last file
        """
        try:
            return int(max(self.data.get('recent_files').keys()))+1
        except:
            return 0
    
    #- READ/WRITE ------
    def read(self, filename=None):
        raw_data = open(self.prefsfile).read()
        self.__data = json.loads(raw_data, object_pairs_hook=dict)

    def write(self, quiet=False, backup=False, **kwargs):
        """
        write the bookmark file
        
        params:
            quiet    - (bool) verbose output
            filename - (str)  filename to write
            backup   - (bool) backup prefs before write 
        """
        filename = kwargs.get('filename', self.prefsfile)
        
        msg = 'writing preferences: "%s"' % filename
        if not os.path.exists(filename):
            msg = 'creating new preferences: "%s"' % filename
        
        
        if len(self.getRecentFiles()) > self.max_items:
            logger.getLogger().info('removing oldest index')  # DEBUG
            self.removeOldestIndex()
        
        # BACKUP
        if backup:
            self.backupPrefs()
        fn = open(filename, 'w')
        try:
            if not quiet:
                logger.getLogger().info(msg)
            json.dump(self.data, fn, indent=4, sort_keys=True)
            fn.close()
            return True
        except:
            self.backupPrefs(restore=True)
            return False

    def backupPrefs(self, **kwargs):
        """ 
        backup the preferences file 
        """
        import shutil
        src_file  = kwargs.get('src', self.prefsfile)
        dest_file = kwargs.get('dest', self.backupprefs)
        restore  = kwargs.get('restore', False)
        msg = 'backing up'
        if restore:
            msg = 'restoring'
            tmp = src_file
            src_file = dest_file
            dest_file = tmp

        if os.path.exists(src_file):
            shutil.copy(src_file, dest_file)
            logger.getLogger().debug('%s preferences: "%s"' % (msg, dest_file))  # DEBUG
        return self.backupprefs

    @property
    def data(self):
        return self.__data

    @property
    def parent(self):
        return self.__parent
    
    @property
    def prefsfile(self):
        return self.__prefsfile

    @property
    def prefsdir(self):
        return self.__prefsdir

    @property
    def backupprefs(self):
        return self.backupprefs

    @property
    def max_items(self):
        return self.__max_items

    @property
    def qtsettings(self):
        return self.__qtsettings