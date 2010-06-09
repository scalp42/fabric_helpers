import os
import time

from fabric import state
from fabric.api import run, sudo, cd, local
from fabric.contrib.files import exists, append
from warnings import warn



class Server(object):
    def __init__(self, name, conf_files_path=None, conf_files=[], 
                    packages=[], pip_packages=[], restart_command=None, 
                    start_command=None):
        self.name = name
        if conf_files_path:
            self.conf_files_path = conf_files_path
        else:
            self.conf_files_path = os.path.join('/etc', name)
        self.conf_files = conf_files
        self.packages=packages
        self.pip_packages = pip_packages
        self.restart_command = restart_command
        if start_command == None:
            self.start_command = self.restart_command
        else:
            self.start_command = start_command

    def start(self):
        if not self.start_command:
            # If the server doesn't need a restart just override this as pass
            raise NotImplementedError, "Start command wasn't specified for this server"
        else:
            sudo(self.start_command)
    
    def restart(self):
        if not self.restart_command:
            # If the server doesn't need a restart just override this as pass
            raise NotImplementedError, "Restart command wasn't specified for this server"
        else:
            sudo(self.restart_command)

    def code_reload(self):
        # When the code is changed does what should the server do to start 
        # using the new code
        self.restart()
    
    def install(self):
        self.setup()
        self.restart()

    def setup(self):
        self.setup_config_files()
        
    def setup_config_files(self, project_conf_dir=None, server_type=None):
        if self.conf_files:
            if not server_type:
                server_type=state.env.name
            if not project_conf_dir:
                project_conf_dir = os.path.join(state.env.paths['live'], 'config/')
        
            timestamp = time.strftime('%Y%m%d%H%M%S')
            for conf_file in self.conf_files:
                new_file = os.path.join(project_conf_dir, self.name, server_type, conf_file)
                
                if not exists(new_file):
                    #No specific config file for the deployment env (prod, staging, etc) so use the general one
                    new_file = os.path.join(project_conf_dir, self.name, conf_file)
                if exists(new_file):
                    conf_path = os.path.join(self.conf_files_path, conf_file)
                    if exists(conf_path):
                        sudo('mv %s %s-%s.bak' % (conf_path, conf_path, timestamp))
                    sudo('ln -s %s %s' % (new_file, conf_path))
  

class PostgresqlServer(Server):
    def __init__(self, name="postgresql", 
            packages=['postgresql','postgresql-dev'], 
            pip_packages=[''],
            start_command='invoke-rc.d postgresql-8.4 start',
            restart_command='invoke-rc.d postgresql-8.4 restart',
            conf_files_path='/etc/postgresql/8.4/main/',
            conf_files=['pg_hba.conf', 'postgresql.conf'],
            **kwargs):

        super(PostgresqlServer, self).__init__(name, packages=packages, 
            start_command=start_command, 
            restart_command=restart_command, 
            conf_files_path=conf_files_path,
            conf_files=conf_files,
            **kwargs)
    
    def code_reload(self):
        pass

    def setup(self):
        self.setup_config_files()
        # self.create_db()
    
    # def create_db(self):
    #   Currently requires user input, need to determine how to create these without needing user input
    #     run('sudo -u postgres createuser %s' % state.env.DATABASE_USER)
    #     run('sudo -u postgres createdb -O %s %s' % (state.env.DATABASE_USER, state.env.DATABASE_NAME))

class RabbitServer(Server):
    def __init__(self, name='rabbit', packages=['rabbitmq-server'],
            start_command='/etc/init.d/rabbitmq-server start',
            restart_command='/etc/init.d/rabbitmq-server restart',
            **kwargs):
        
        super(RabbitServer, self).__init__(name, **kwargs)

    def setup_config(self):
        sudo("rabbitmqctl add_user %s rabbitpass" % state.env.user)
        sudo("rabbitmqctl add_vhost %s" % state.env.project_name)
        sudo('rabbitmqctl map_user_vhost %s gr_select' % state.env.user)
    
    def code_reload(self):
        pass


class CeleryServer(Server):
    def __init__(self, name='celery', 
            packages=['rabbitmq-server'],
            pip_packages=['celery==1.0.5'],
            start_command='/etc/init.d/celeryd start', 
            restart_command='/etc/init.d/celeryd restart', 
            **kwargs):
        
        super(CeleryServer, self).__init__(name, **kwargs)


    def setup_config(self):
        run('mkdir %s' % os.path.join(state.env.paths['root'], 'celery'))
        sudo('ln %s /etc/init.d/celeryd') % (os.path.join(state.env.paths['live'], 'config/init_scripts/celeryd'))
        sudo('chmod +x /etc/init.d/celeryd')
        sudo('update-rc.d celeryd defaults')

