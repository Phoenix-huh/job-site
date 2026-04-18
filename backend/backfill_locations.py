"""
Script to backfill the 'location' column for existing jobs.
Scans title and description for over 100 Indian city names using robust regex.
"""
import os
import sys
import re

# Ensure backend directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import models
from database import SessionLocal

# Common Indian cities and regions to look for (Tier 1, 2, and major 3)
CITIES = [
    # Tier 1 & Metro
    "Mumbai", "Bangalore", "Bengaluru", "Delhi", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", "Pune",
    "Gurgaon", "Gurugram", "Noida", "Greater Noida", "Faridabad", "Ghaziabad", "New Delhi", "NCR",
    
    # Tier 2 & Major Cities
    "Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Pimpri-Chinchwad",
    "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot", 
    "Kalyan-Dombivli", "Vasai-Virar", "Varanasi", "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Navi Mumbai",
    "Allahabad", "Howrah", "Ranchi", "Gwalior", "Jabalpur", "Coimbatore", "Vijayawada", "Jodhpur", "Madurai", 
    "Raipur", "Chandigarh", "Guwahati", "Solapur", "Hubli", "Dharwad", "Bareilly", "Moradabad", "Mysore", 
    "Aligarh", "Jalandhar", "Tiruchirappalli", "Bhubaneswar", "Salem", "Mira-Bhayandar", "Warangal", 
    "Guntur", "Bhiwandi", "Saharanpur", "Gorakhpur", "Bikaner", "Amravati", "Jamshedpur", "Bhilai", 
    "Cuttack", "Firozabad", "Kochi", "Nellore", "Bhavnagar", "Dehradun", "Durgapur", "Asansol", "Rourkela", 
    "Nanded", "Kolhapur", "Ajmer", "Akola", "Gulbarga", "Jamnagar", "Ujjain", "Loni", "Siliguri", "Jhansi", 
    "Ulhasnagar", "Jammu", "Mangalore", "Erode", "Belgaum", "Ambattur", "Tirunelveli", 
    "Malegaon", "Gaya", "Jalgaon", "Udaipur", "Maheshtala", "Davanagere", "Kozhikode", "Akurnji", "Rajpur Sonarpur", 
    "Rajahmundry", "Bokaro", "South Dumdum", "Bellary", "Patiala", "Gopalpur", "Agartala", "Bhagalpur", "Muzaffarnagar", 
    "Bhatpara", "Panihati", "Latur", "Dhule", "Rohtak", "Korba", "Bhillai", "Brahmapur", "Muzaffarpur", "Ahmednagar", 
    "Kollam", "Avadi", "Rajarhat", "Kadapa", "Kamarhati", "Bilaspur", "Shahjahanpur", "Bijapur", "Kurnool", 
    "Shivamogga", "Thrissur", "Yamunanagar", "Panipat", "Darbhanga", "Alwar", "Kakinada", "Nizamabad", "Ichalkaranji",
    "Pondicherry", "Puducherry", "Shimla", "Panaji", "Goa", "Gandhinagar", "Itanagar", "Imphal", "Shillong", "Kohima", "Aizawl",
    
    # Common Work Modes
    "Remote", "Work from Home", "WFH", "Anywhere in India"
]

def backfill():
    db = SessionLocal()
    try:
        # Get jobs where location is missing
        jobs = db.query(models.Job).filter(
            (models.Job.location == None) | (models.Job.location == "")
        ).all()
        
        print(f"Checking {len(jobs)} jobs for location backfill (using Regex)...")
        updated_count = 0
        
        for job in jobs:
            found_city = None
            
            # 1. Check Title (High Priority)
            for city in CITIES:
                if re.search(r'\b' + re.escape(city) + r'\b', job.title, re.IGNORECASE):
                    found_city = city
                    break
            
            # 2. Check Description (Lower Priority)
            if not found_city:
                for city in CITIES:
                    if re.search(r'\b' + re.escape(city) + r'\b', job.description, re.IGNORECASE):
                        found_city = city
                        break
            
            if found_city:
                job.location = found_city
                updated_count += 1
                if updated_count % 20 == 0:
                    print(f"  Processed {updated_count} updates...")
        
        db.commit()
        print(f"Successfully updated {updated_count} jobs with backfilled locations.")
        
    except Exception as e:
        db.rollback()
        print(f"Error during backfill: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill()
