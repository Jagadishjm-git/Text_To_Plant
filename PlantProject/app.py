from flask import Flask, render_template, request
from predict import predict_plant
from formatter import format_results

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    results = []

    if request.method == "POST":
        user_input = request.form["description"]
        matches = predict_plant(user_input)
        results = format_results(matches)

    return render_template("index.html", results=results)

if __name__ == "__main__":
    app.run(debug=True)
