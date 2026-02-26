from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
import pdfkit


app = Flask(__name__)

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
def home():
    # Bazaba budagiyoya variable-ba muguzaronem 
    projects = Project.query.all()
    return render_template('index.html', projects=projects)


@app.route('/add_project', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        # a Forma omaysudagi malumota giftan
        p_name = request.form.get('name')
        c_name = request.form.get('client_name')

        # Nav obyekt soxtan (a Project klassash)
        new_project = Project(name=p_name, client_name=c_name)

        # Bazaba soxranit kadan
        db.session.add(new_project)
        db.session.commit()

        return redirect(url_for('home'))
    
    return render_template('add_project.html')

# DYNAMIC ROUTE

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    # project_id kadi a baza proetkta yoftan
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)

@app.route('/add_item/<int:project_id>', methods = ['POST'])
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
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)

    db.session.delete(project)
    db.session.commit()

    return redirect(url_for('home',))


# EDIT ITEM

@app.route('/edit_item/<int:item_id>', methods = ['POST', 'GET'])
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


# PDF-kit
@app.route('/project/<int:project_id>/pdf')
def export_pdf(project_id):
    project = Project.query.get_or_404(project_id)

    # baroi PDF prostoycha HTML tayyor mukunem
    rendered = render_template('project_pdf.html', project=project)

    #wkhtmltopdf programmesha adressash
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    # a HTML PDF soxtan
    pdf = pdfkit.from_string(rendered, False, configuration=config)

    # Brauzerba pdf file kada fursondan
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=otchot_{project_id}.pdf'
    
    return response



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)