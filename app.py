from flask import Flask, flash, render_template, request, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy

#pdf
import platform
import pdfkit

# baroi LOGIN
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash




app = Flask(__name__)

app.config['SECRET_KEY'] = 'in-gandeshba-sekretniy-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ustolist.db'

# database in mesozem pomemu egzemplar
db = SQLAlchemy()

# db-ya appba connect mukunem
db.init_app(app)


# MODEL

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True ) #primary_key=True har yakta proektba unikal nomer
    name = db.Column(db.String(100), nullable = False ) #obyekt nomash #nullable = False pustoy shudagesh mumkin ne
    client_name = db.Column(db.String(100))
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp()) # Proekt soxta shudageshba
    # server vaqtasha avtomaticheski navesta memonad

    #baroi login
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # ???
    items = db.relationship('Item', backref='project', lazy=True, cascade="all, delete-orphan")
    #cascade="all, delete-orphan" agar proekt delete shavad itemoyam delete kun

    def total_price(self):
        # Hamma mahulota narxasha hisob kada medodagi method
        # return sum(item.total()for item in self.items) # List comprehension qiyind
        summa = 0

        for item in self.items:
            summa = summa + item.total()
        
        return summa
    


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable = False) # Nomi mahsulot (Samarez)
    quantity = db.Column(db.Float, default=1.0) # Chanta
    unit_price = db.Column(db.Float, nullable = False) # Dona narxash
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    def total(self):
        #yakta mahsulota summesh: $quantity \times unit\_price$
        return self.quantity * self.unit_price



@app.route('/')
@login_required
def home():
    # Bazaba budagiyoya variable-ba muguzaronem 
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', projects=projects)


@app.route('/add_project', methods=['GET', 'POST'])
@login_required
def add_project():
    if request.method == 'POST':
        # a Forma omaysudagi malumota giftan
        p_name = request.form.get('name')
        c_name = request.form.get('client_name')

        # Nav obyekt soxtan (a Project klassash)
        new_project = Project(name=p_name, client_name=c_name, user_id=current_user.id)

        # Bazaba soxranit kadan
        db.session.add(new_project)
        db.session.commit()

        return redirect(url_for('home'))
    
    return render_template('add_project.html')

# DYNAMIC ROUTE

@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    # project_id kadi a baza proetkta yoftan
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)

@app.route('/add_item/<int:project_id>', methods = ['POST'])
@login_required
def add_item(project_id):
    # a Forma malumot giftan
    name = request.form.get('name')
    quantity = float(request.form.get('quantity'))
    unit_price = float(request.form.get('unit_price'))

    # nav mahsulot soxta proektba qo'shi kadan
    new_item = Item(
        name=name,
        quantity=quantity,
        unit_price=unit_price,
        project_id=project_id, # mana mainjaba mahsulot proektba qo'shi mushud

    )

    db.session.add(new_item)
    db.session.commit()

    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/delete_item/<int:item_id>')
@login_required
def delete_item(item_id):
    # O'chiri kadan darkor budagi mahsulota meyobem
    item  = Item.query.get_or_404(item_id)
    p_id  = item.project_id # a o'chiri shudan pesh proekta ID-yasha
    # esla kada memonem

    db.session.delete(item) # a baza DELETE
    db.session.commit() # O'zgarisha tasdiqla mukunem 

    # Bo hamun proekta page-ashba gashta merem
    return redirect(url_for('project_detail', project_id=p_id))


@app.route('/delete_project/<int:project_id>')
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)

    db.session.delete(project)
    db.session.commit()

    return redirect(url_for('home',))


# EDIT ITEM

@app.route('/edit_item/<int:item_id>', methods = ['POST', 'GET'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id) # Edit mushudagi mahsulota meyobem

    if request.method == "POST":
        # a Forma nav malumotoya migirem
        item.name = request.form.get('name')
        item.quantity = float(request.form.get('quantity'))
        item.unit_price = float(request.form.get('unit_price'))

        db.session.commit() # O'zgarishoya save mukunem
        return redirect(url_for('project_detail', project_id=item.project_id))
    
    # Agar GET boshad, hamun Edit page-a nishon mitem
    return render_template('edit_item.html', item=item)


#LOGIN
# Login managerni to'g'ri kadan
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Login nakadagi boshad, gijoba fursondan

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(120))

    #User ki Projecta miyoneshba budagi connect
    projects = db.relationship('Project', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Xato login yoki parol!')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))




# PDF-kit
@app.route('/project/<int:project_id>/pdf')
def export_pdf(project_id):
    project = Project.query.get_or_404(project_id)

    # baroi PDF prostoycha HTML tayyor mukunem
    rendered = render_template('project_pdf.html', project=project)

    #agar windows boshad(Lokal komp)
    if platform.system() =='Windows':
        path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    else:
        # Agar Linux boshad (Pythonanywhere)
        config = pdfkit.configuration()
    
    # baroi (harfoi sh ch o' darkor)
    options = {
        'encoding': "UTF-8",
        'no-outline': None,
        'quiet': ''
    }
    # a HTML PDF soxtan
    try:
        pdf = pdfkit.from_string(rendered, False, configuration=config)
    except Exception as e:
        return f"PDF yaratishda xato: {str(e)}"

    # Brauzerba pdf file kada fursondan
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=otchot_{project.name}.pdf'
    
    return response



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)