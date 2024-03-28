from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import uuid
import traceback
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///routes.db'
db = SQLAlchemy(app)


# Define the Route model
class Route(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    data = db.Column(db.JSON)

    def __init__(self, data):
        self.id = str(uuid.uuid4())
        self.data = data


# Create the database tables
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        stops = []
        etas = []

        # Extract form data and perform calculations
        num_stops = int(request.form['num_stops'])
        arrival_time = datetime.strptime(request.form['stop1Arrival'], '%H:%M')

        for i in range(1, num_stops + 1):
            name = request.form[f'stop{i}Name']
            work_duration = int(request.form[f'stop{i}Duration'])
            travel_time = int(request.form[f'stop{i}Travel'])

            # Calculate ETA for each stop
            if i == 1:
                eta = arrival_time
            else:
                prev_eta = etas[-1]
                prev_work_duration = int(request.form[f'stop{i - 1}Duration'])
                prev_travel_time = int(request.form[f'stop{i - 1}Travel'])
                eta = calculate_eta(prev_eta, prev_work_duration, prev_travel_time)

            stops.append({'name': name, 'eta': eta.strftime('%I:%M %p')})
            etas.append(eta)

        # Calculate ETA back home
        last_stop_eta = etas[-1]
        last_stop_work_duration = int(request.form[f'stop{num_stops}Duration'])
        last_stop_travel_time = int(request.form[f'stop{num_stops}Travel'])
        eta_back_home = calculate_eta(last_stop_eta, last_stop_work_duration, last_stop_travel_time)

        # Generate unique ID and store route data in the database
        route_data = {
            'stops': stops,
            'eta_back_home': eta_back_home.strftime('%I:%M %p')
        }
        route = Route(data=route_data)
        db.session.add(route)
        db.session.commit()

        # Redirect to the calculated route page with the unique ID
        return redirect(url_for('calculated_route', route_id=route.id))

    except Exception as e:
        app.logger.error(f"Error occurred while calculating the route: {str(e)}")
        app.logger.error(traceback.format_exc())
        return "An error occurred while calculating the route", 500


@app.route('/route/<route_id>')
def calculated_route(route_id):
    # Retrieve the route data from the database based on the route_id
    route = Route.query.get(route_id)
    if route:
        # Pass the route data to the calc.html template
        return render_template('calc.html', route=route.data)
    else:
        # Handle case when route is not found
        return "Route not found", 404


def calculate_eta(prev_eta, work_duration, travel_time):
    # Calculate the ETA based on the previous ETA, work duration, and travel time
    eta = prev_eta + timedelta(minutes=work_duration + travel_time)

    # Round up to the nearest 15 minutes
    minutes = eta.minute
    if minutes % 15 != 0:
        minutes = (minutes // 15 + 1) * 15
        eta = eta.replace(minute=0, second=0, microsecond=0)
        eta += timedelta(minutes=minutes)

    return eta


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

