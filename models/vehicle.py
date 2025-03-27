from extensions import db
from datetime import datetime

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50))
    model = db.Column(db.String(50))
    color = db.Column(db.String(20))
    seats = db.Column(db.Integer)
    purchase_date = db.Column(db.Date)
    mileage = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='可用')  # 可用, 维修中, 预约中, 不可用
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    
    # 关系
    driver = db.relationship('User', backref='driven_vehicles')
    applications = db.relationship('Application', back_populates='vehicle')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Vehicle {self.plate_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'plate_number': self.plate_number,
            'vehicle_type': self.vehicle_type,
            'brand': self.brand,
            'model': self.model,
            'color': self.color,
            'seats': self.seats,
            'status': self.status,
            'driver': self.driver.name if self.driver else None
        } 