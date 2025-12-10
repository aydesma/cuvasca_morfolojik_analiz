from flask import Flask, render_template, request
from morphology import analyze
import os

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    final_word = ""
    root_word = ""
    
    # Seçimleri korumak için değişkenler
    selected_sahis = ""
    selected_plural = False
    
    if request.method == 'POST':
        root = request.form.get('root', '').strip()
        root_word = root
        
        # Parametreleri al
        sahis_code = request.form.get('sahis')
        is_plural = request.form.get('plural') == 'on'
        
        # Seçimleri koru
        selected_sahis = sahis_code if sahis_code else ""
        selected_plural = is_plural
        
        if root:
            parts, final_word = analyze(root, sahis_code, is_plural)
            result = parts
            
    return render_template('index.html', 
                         result=result, 
                         final_word=final_word, 
                         root=root_word, 
                         selected_sahis=selected_sahis,
                         selected_plural=selected_plural)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
