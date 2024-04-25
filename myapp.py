# USERNAME: umakscheduler
# PASSWORD: Adminschedule123

from flask import Flask, render_template, redirect, request, session, url_for
from flask_session import Session
from werkzeug.utils import secure_filename
import os
import pypyodbc as odbc
import process_excel as pe
import alert_files.admin_alert as admin_alert
import alert_files.user_alert as user_alert
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

app.config["UPLOAD_FOLDER"] = "static/files/"
ALLOWED_EXTENSIONS = {'xlsx'}
Session(app)

server = 'umakscheduler.database.windows.net'
database = 'SchedulerDB'
connString = 'Driver={ODBC Driver 18 for SQL Server};Server=tcp:'+server+',1433;Database='+database+';Uid=umakscheduler;Pwd=Adminschedule123;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

@app.route('/')
def home():
    if 'userId' not in session:
        return redirect(url_for('login')) # IF: Not logged in, redirect to login page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        currentEmployeeId = request.form['employeeId']
        currentPassword = request.form['password']
        query = f"SELECT * FROM Professors WHERE employeeId = {currentEmployeeId} AND employeePassword = '{currentPassword}'"
        result = executeQuery(query)
        
        if result:
            if currentEmployeeId != 0000 and currentPassword != 'admin':
                session["userId"] = currentEmployeeId
                return redirect(url_for('index'))
            else:
                # IF: User is 'admin': proceed to Admin Portal
                session['userId'] = '0000'
                return redirect(url_for('admin'))
        
        return user_alert.invalid_login_credentials()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_EmployeeId = request.form['employeeId']
        new_EmployeeName = request.form['employeeName']
        new_EmployeePassword = request.form['password']

        checkQuery = f"SELECT * FROM Professors WHERE employeeId = {new_EmployeeId}"
        insertQuery = f"INSERT INTO Professors (employeeId, employeeName, employeePassword, employeeSchedule) VALUES ({new_EmployeeId}, '{new_EmployeeName}', '{new_EmployeePassword}', 'Incomplete')"
        insertHonorariumToken = f"INSERT INTO Courses (courseId, courseName, courseYear, courseUnits, professorId) VALUES ('{'HT' + new_EmployeeId}', 'Honorarium Time', '', 0, {new_EmployeeId})"
        insertVacantToken = f"INSERT INTO Courses (courseId, courseName, courseYear, courseUnits, professorId) VALUES ('{'VT' + new_EmployeeId}', 'Vacant Time', '', 0, {new_EmployeeId})"
        checkResult = executeQuery(checkQuery)

        if checkResult: # IF: an existing professorId is detected -> return redirect('/register')
            return user_alert.invalid_existing_user()
        else:
            executeQuery(insertQuery)
            executeQuery(insertHonorariumToken)
            executeQuery(insertVacantToken)
            return user_alert.success_registration()
 
    return render_template('register.html')

@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'userId' not in session:
        return redirect(url_for("login")) # IF: Not logged in, redirect to login page
    
    else:
        
        currentId = int(session['userId'])
        getProfessorsQuery = "SELECT employeeId, employeeName, employeeSchedule FROM Professors WHERE employeeId != 0000"
        professorData = executeQuery(getProfessorsQuery)

        getCoursesQuery = "SELECT * FROM Courses"
        courseData = executeQuery(getCoursesQuery)

        getCourseSchedulesQuery = "SELECT * FROM CourseSchedules"
        scheduleData = executeQuery(getCourseSchedulesQuery)

        if request.method == 'POST':
            action = request.form['btn']

            if action == 'logout':
                session.pop('userId', 0)
                return user_alert.success_user_logout()

            if action == 'submitInquiry':
                inquirySubject = request.form['messageSubject']
                inquiryMessage = request.form['message']
                insertInquiryQuery = f"INSERT INTO ProfessorInquiries (professorId, inqSubject, inqMessage, inqStatus) VALUES ({currentId}, '{inquirySubject}', '{inquiryMessage}', 'Unresolved')"
                executeQuery(insertInquiryQuery)
                return user_alert.success_submit_inquiry()

        return render_template("index.html",
        current_professor=currentId,
        professorData=professorData,
        courseData=courseData,
        scheduleData=scheduleData)

# CODE BLOCK: Admin Page
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'userId' not in session or session['userId'] != '0000':
        return redirect(url_for("login")) # IF: Not logged in, redirect to login page
         
    else:
        getProfessorsQuery = "SELECT employeeId, employeeName, employeeSchedule FROM Professors WHERE employeeId != 0000"
        professorData = executeQuery(getProfessorsQuery)

        getCoursesQuery = "SELECT * FROM Courses"
        courseData = executeQuery(getCoursesQuery)

        getCourseSchedulesQuery = "SELECT * FROM CourseSchedules"
        scheduleData = executeQuery(getCourseSchedulesQuery)

        getRoomsQuery = "SELECT * FROM Rooms"
        roomData = executeQuery(getRoomsQuery)
        

        for prof in professorData:
            print(prof[1])

        current_professor = 0 # INIT: No value needed
        scheduleMode = 0 # INIT: No value needed
        
        if request.method == "POST":
            action = request.form['btn']
            

            if action == 'backToAdmin':
                return redirect("/admin")

            if action == 'logout':
                session.pop('userId', 0)
                return admin_alert.success_admin_logout()

            if action == 'addCourse':
                newCourseCode = request.form['courseCode'].upper()
                newCourseName = request.form['courseName'].upper()
                newCourseYear = request.form['courseYear']
                newCourseUnits = request.form['courseUnits']
                newCourseType = request.form['courseType']
                checkQuery = f"SELECT * FROM Courses WHERE courseId = '{newCourseCode}'"
                insertQuery = f"INSERT INTO Courses (courseId, courseName, courseYear, courseUnits, courseType) VALUES ('{newCourseCode}', '{newCourseName}', '{newCourseYear}', {newCourseUnits}, '{newCourseType}')"
                checkResult = executeQuery(checkQuery)

                if checkResult:
                    return admin_alert.invalid_course_exists(newCourseCode)
                else:
                    executeQuery(insertQuery)
                    professorData = executeQuery(getProfessorsQuery)
                    courseData = executeQuery(getCoursesQuery)
                    scheduleData = executeQuery(getCourseSchedulesQuery)
                    roomData = executeQuery(getRoomsQuery)
                    current_professor = int(current_professor)
                    return admin_alert.success_course_add(newCourseCode)

            if action == 'checkProfessorSchedule':
                scheduleMode = 1
                try:
                    current_professor = request.form['hiddenProfessorDetails']
                    request.form
                except:
                    return redirect(url_for('admin'))

            if action == 'setHonorariumVacantTime':
                scheduleMode = 2
                try:
                    current_professor = request.form['hiddenProfessorDetails']
                except:
                    return redirect(url_for('admin'))

            if action == 'manageCourse':
                scheduleMode = 1
                currentType = ""
                maxHours = 0
                genEdImplicitDays = ['Monday', 'Tuesday', 'Thursday', 'Friday']
                current_course = request.form['currentCourse'].upper()
                current_professor = request.form['hiddenProfessorDetails']
                newCourseSection = request.form['courseSection'].upper()
                newStartTime = request.form['startTime']
                newEndTime = request.form['endingTime']
                newDayOfWeek = request.form['dayOfWeek']
                newRoom = request.form['courseRoom'].upper()
                courseDuration = float(request.form['courseDuration'].upper())

                if newRoom == "":
                    newRoom = "Virtual"

                ifProfessorExists = False
                ifNoProfessorExists = False

                for courses in courseData:
                    if courses[0] == current_course and courses[4] == int(current_professor):
                        ifProfessorExists = True
                        break

                for courses in courseData:
                    if courses[0] == current_course and courses[4] is None:
                        ifNoProfessorExists = True
                        break

                insertScheduleQuery = f"INSERT INTO CourseSchedules (courseId, professorId, room, section, dayOfWeek, startTime, endTime) VALUES "
                updateCourseQuery = f"UPDATE Courses SET professorId = {current_professor} WHERE courseId = '{current_course}'"
                checkIfSameTime = f"SELECT * FROM CourseSchedules WHERE courseId = '{current_course}' and startTime = '{newStartTime}' AND endTime = '{newEndTime}' and dayOfWeek = '{newDayOfWeek}'"
                checkCourseType = f"SELECT courseType FROM Courses WHERE courseId = '{current_course}'"
                checkIfSameRoom = f"SELECT * FROM CourseSchedules WHERE startTime = '{newStartTime}' and endTime = '{newEndTime}' and dayOfWeek = '{newDayOfWeek}' and room = '{newRoom}'"
                sameRoom = executeQuery(checkIfSameRoom)

                getCourseType = executeQuery(checkCourseType)
                for types in getCourseType:
                    currentType = types[0]
                
                if currentType == 'Major':
                    maxHours = 3
                else:
                    maxHours = 1.5

                if newDayOfWeek in genEdImplicitDays and currentType == 'GenEd':
                    print("ERROR: You cannot schedule GenEd classes on these specific days. Try again.")
                else:
                    if courseDuration != 3:  # Check if courseDuration is not 3
                        if newDayOfWeek == "Monday" or newDayOfWeek == "Thursday":
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Monday', '{newStartTime}', '{newEndTime}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Thursday', '{newStartTime}', '{newEndTime}')"
                        elif newDayOfWeek == "Tuesday" or newDayOfWeek == "Friday":
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Tuesday', '{newStartTime}', '{newEndTime}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Friday', '{newStartTime}', '{newEndTime}')"
                        elif newDayOfWeek == "Wednesday" or newDayOfWeek == "Saturday":
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Wednesday', '{newStartTime}', '{newEndTime}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Saturday', '{newStartTime}', '{newEndTime}')"

                    if courseDuration == 3:
                        if newDayOfWeek == "Monday":
                            # Define the initial times
                            start_time = datetime.strptime(newStartTime, "%H:%M:%S").time()
                            end_time = datetime.strptime(newEndTime, "%H:%M:%S").time()
                            # Calculate the middle time
                            middle_seconds = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).total_seconds() / 2
                            middle_time = (datetime.combine(datetime.today(), start_time) + timedelta(seconds=middle_seconds)).time()
                            middle_time_str = middle_time.strftime("%I:%M %p")
                            # Print the divided times
                            print(f"{start_time.strftime('%I:%M %p')} - {middle_time_str}")
                            print(f"{middle_time_str} - {end_time.strftime('%I:%M %p')}")
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Monday', '{start_time.strftime('%I:%M %p')}', '{middle_time_str}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Monday', '{middle_time_str}', '{end_time.strftime('%I:%M %p')}')"
                        elif newDayOfWeek == "Tuesday":
                                # Define the initial times
                            start_time = datetime.strptime(newStartTime, "%H:%M:%S").time()
                            end_time = datetime.strptime(newEndTime, "%H:%M:%S").time()
                                    # Calculate the middle time
                            middle_seconds = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).total_seconds() / 2
                            middle_time = (datetime.combine(datetime.today(), start_time) + timedelta(seconds=middle_seconds)).time()
                            middle_time_str = middle_time.strftime("%I:%M %p")
                                        # Print the divided times
                            print(f"{start_time.strftime('%I:%M %p')} - {middle_time_str}")
                            print(f"{middle_time_str} - {end_time.strftime('%I:%M %p')}")
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Tuesday', '{start_time.strftime('%I:%M %p')}', '{middle_time_str}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Tuesday', '{middle_time_str}', '{end_time.strftime('%I:%M %p')}')"
                        elif newDayOfWeek == "Wednesday":
                                # Define the initial times
                            start_time = datetime.strptime(newStartTime, "%H:%M:%S").time()
                            end_time = datetime.strptime(newEndTime, "%H:%M:%S").time()
                                    # Calculate the middle time
                            middle_seconds = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).total_seconds() / 2
                            middle_time = (datetime.combine(datetime.today(), start_time) + timedelta(seconds=middle_seconds)).time()
                            middle_time_str = middle_time.strftime("%I:%M %p")
                                        # Print the divided times
                            print(f"{start_time.strftime('%I:%M %p')} - {middle_time_str}")
                            print(f"{middle_time_str} - {end_time.strftime('%I:%M %p')}")
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Wednesday', '{start_time.strftime('%I:%M %p')}', '{middle_time_str}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Wednesday', '{middle_time_str}', '{end_time.strftime('%I:%M %p')}')"
                        elif newDayOfWeek == "Thursday":
                                # Define the initial times
                            start_time = datetime.strptime(newStartTime, "%H:%M:%S").time()
                            end_time = datetime.strptime(newEndTime, "%H:%M:%S").time()
                                    # Calculate the middle time
                            middle_seconds = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).total_seconds() / 2
                            middle_time = (datetime.combine(datetime.today(), start_time) + timedelta(seconds=middle_seconds)).time()
                            middle_time_str = middle_time.strftime("%I:%M %p")
                                        # Print the divided times
                            print(f"{start_time.strftime('%I:%M %p')} - {middle_time_str}")
                            print(f"{middle_time_str} - {end_time.strftime('%I:%M %p')}")
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Thursday', '{start_time.strftime('%I:%M %p')}', '{middle_time_str}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Thursday', '{middle_time_str}', '{end_time.strftime('%I:%M %p')}')"
                        elif newDayOfWeek == "Friday":
                                # Define the initial times
                            start_time = datetime.strptime(newStartTime, "%H:%M:%S").time()
                            end_time = datetime.strptime(newEndTime, "%H:%M:%S").time()
                                    # Calculate the middle time
                            middle_seconds = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).total_seconds() / 2
                            middle_time = (datetime.combine(datetime.today(), start_time) + timedelta(seconds=middle_seconds)).time()
                            middle_time_str = middle_time.strftime("%I:%M %p")
                                        # Print the divided times
                            print(f"{start_time.strftime('%I:%M %p')} - {middle_time_str}")
                            print(f"{middle_time_str} - {end_time.strftime('%I:%M %p')}")
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Friday', '{start_time.strftime('%I:%M %p')}', '{middle_time_str}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Friday', '{middle_time_str}', '{end_time.strftime('%I:%M %p')}')"
                        elif newDayOfWeek == "Saturday":
                                # Define the initial times
                            start_time = datetime.strptime(newStartTime, "%H:%M:%S").time()
                            end_time = datetime.strptime(newEndTime, "%H:%M:%S").time()
                                    # Calculate the middle time
                            middle_seconds = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).total_seconds() / 2
                            middle_time = (datetime.combine(datetime.today(), start_time) + timedelta(seconds=middle_seconds)).time()
                            middle_time_str = middle_time.strftime("%I:%M %p")
                                        # Print the divided times
                            print(f"{start_time.strftime('%I:%M %p')} - {middle_time_str}")
                            print(f"{middle_time_str} - {end_time.strftime('%I:%M %p')}")
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Saturday', '{start_time.strftime('%I:%M %p')}', '{middle_time_str}'), "
                            insertScheduleQuery += f"('{current_course}', {current_professor}, '{newRoom}', '{newCourseSection}', 'Saturday', '{middle_time_str}', '{end_time.strftime('%I:%M %p')}')"
                        
                    
                    print(insertScheduleQuery)

                    checkExceedsHours = f"""
                                            SELECT cs.professorId, 
                                                SUM(DATEDIFF(MINUTE, cs.startTime, cs.endTime) / 60.0) AS totalScheduledHours
                                            FROM CourseSchedules cs
                                            JOIN Courses c ON cs.courseId = c.courseId
                                            WHERE cs.professorId = {current_professor}
                                            AND cs.courseId = '{current_course}'
                                            AND c.courseType = '{currentType}'
                                            GROUP BY cs.professorId
                                            HAVING SUM(DATEDIFF(MINUTE, cs.startTime, cs.endTime) / 60.0) >= {maxHours};
                                            """
                                
                        # Check if there are existing schedules for the professor and course
                    if scheduleData:
                        # If there is a professor assigned to the course
                        if ifProfessorExists:
                            if sameRoom:
                                return admin_alert.invalid_existing_room(sameRoom)
                            else:
                                if executeQuery(checkIfSameTime):
                                    return admin_alert.invalid_existing_course_timeslot(current_course)
                                else:
                                    if executeQuery(checkExceedsHours):
                                        # Check if the course is being assigned to a different section for the same professor
                                        existing_course_section_query = f"SELECT section FROM CourseSchedules WHERE courseId = '{current_course}' AND professorId = {current_professor}"
                                        existing_course_section = executeQuery(existing_course_section_query)
                                        if existing_course_section and newCourseSection not in [section[0] for section in existing_course_section]:
                                            # Different section for the same professor
                                            executeQuery(insertScheduleQuery)
                                            professorData = executeQuery(getProfessorsQuery)
                                            courseData = executeQuery(getCoursesQuery)
                                            scheduleData = executeQuery(getCourseSchedulesQuery)
                                            roomData = executeQuery(getRoomsQuery)
                                            current_professor = int(current_professor)
                                            scheduleMode = scheduleMode
                                        else:
                                            print("ERROR: Course is already assigned to the same section or professor.")
                                    else:
                                        executeQuery(insertScheduleQuery)
                                        professorData = executeQuery(getProfessorsQuery)
                                        courseData = executeQuery(getCoursesQuery)
                                        scheduleData = executeQuery(getCourseSchedulesQuery)
                                        roomData = executeQuery(getRoomsQuery)
                                        current_professor = int(current_professor)
                                        scheduleMode = scheduleMode
                        else:
                            # No professor assigned to the course
                            if sameRoom:
                                return admin_alert.invalid_existing_room(sameRoom)
                            else:
                                if executeQuery(checkIfSameTime):
                                    return admin_alert.invalid_existing_course_timeslot(current_course)
                                else:
                                    if executeQuery(checkExceedsHours):
                                        return admin_alert.invalid_maximum_timeslot(current_course, currentType)
                                    else:
                                        # No issues found, proceed with inserting the schedule
                                        executeQuery(insertScheduleQuery)
                                        executeQuery(updateCourseQuery)  # Update course information
                                        # Update necessary data for UI refresh
                                        professorData = executeQuery(getProfessorsQuery)
                                        courseData = executeQuery(getCoursesQuery)
                                        scheduleData = executeQuery(getCourseSchedulesQuery)
                                        roomData = executeQuery(getRoomsQuery)
                                        current_professor = int(current_professor)
                                        scheduleMode = scheduleMode
                    else:  # If no records exist, insert new schedule into the table
                        executeQuery(insertScheduleQuery)
                        executeQuery(updateCourseQuery)  # Update course information
                        # Update necessary data for UI refresh
                        professorData = executeQuery(getProfessorsQuery)
                        courseData = executeQuery(getCoursesQuery)
                        scheduleData = executeQuery(getCourseSchedulesQuery)
                        roomData = executeQuery(getRoomsQuery)
                        current_professor = int(current_professor)
                        scheduleMode = scheduleMode

            if action == 'insertHonorariumVacant':
                scheduleMode = 2
                current_professor = request.form['hiddenProfessorDetails']
                otherScheduleType = request.form['honorVacantChoice']
                honorVacantDayOfWeek = request.form['honorVacantDayOfWeek']
                honorVacantStartTime = request.form['honorVacantStartTime']
                honorVacantEndTime = request.form['honorVacantEndingTime']
                
                getHonorariumID = f"SELECT courseId FROM Courses where courseId = '{'HT' + current_professor}'"
                getVacantID = f"SELECT courseId FROM Courses where courseId = '{'VT' + current_professor}'"
                honorIDquery = executeQuery(getHonorariumID)
                vacantIDquery = executeQuery(getVacantID)

                if otherScheduleType == 'Honorarium Time':
                    choiceID = honorIDquery[0][0]
                
                if otherScheduleType == 'Vacant Time':
                    choiceID = vacantIDquery[0][0]

                insertHonorVacantQuery = f"INSERT INTO CourseSchedules (courseId, professorId, room, section, dayOfWeek, startTime, endTime) VALUES ('{choiceID}', {current_professor}, '', '', '{honorVacantDayOfWeek}', '{honorVacantStartTime}', '{honorVacantEndTime}')"
                checkSameHonorVacantTime = f"SELECT * FROM CourseSchedules WHERE startTime = '{honorVacantStartTime}' AND endTime = '{honorVacantEndTime}' AND dayOfWeek = '{honorVacantDayOfWeek}'"
                checkExceedsHourMins = f"""
                                        SELECT professorId, 
                                            SUM(DATEDIFF(MINUTE, startTime, endTime) / 60.0) AS totalScheduledHours
                                        FROM CourseSchedules
                                        WHERE professorId = {int(current_professor)}
                                        AND courseId = '{choiceID}'
                                        AND dayOfWeek = '{honorVacantDayOfWeek}'
                                        GROUP BY professorId
                                        HAVING SUM(DATEDIFF(MINUTE, startTime, endTime) / 60.0) >= 1.5;
                                        """

                if scheduleData:
                    if (executeQuery(checkSameHonorVacantTime)):
                        return admin_alert.invalid_existing_honorVacant_timeslot(otherScheduleType)
                    else:
                        if (executeQuery(checkExceedsHourMins)):
                            return admin_alert.invalid_maximum_honorVacant_timeslot(otherScheduleType)
                        else:
                            executeQuery(insertHonorVacantQuery)
                            professorData = executeQuery(getProfessorsQuery)
                            courseData = executeQuery(getCoursesQuery)
                            scheduleData = executeQuery(getCourseSchedulesQuery)
                            roomData = executeQuery(getRoomsQuery)
                            current_professor=int(current_professor)
                            scheduleMode=scheduleMode
                else:
                    executeQuery(insertHonorVacantQuery)
                    professorData = executeQuery(getProfessorsQuery)
                    courseData = executeQuery(getCoursesQuery)
                    scheduleData = executeQuery(getCourseSchedulesQuery)
                    roomData = executeQuery(getRoomsQuery)
                    current_professor=int(current_professor)
                    scheduleMode=scheduleMode

            if action == "deleteCourses":
                selectedCourseIds = request.form.getlist("coursesToBeDeleted")
                for courseId in selectedCourseIds:
                    deleteFromCourses = f"DELETE FROM Courses WHERE courseId = '{courseId}'"
                    deleteFromCourseSchedules = f"DELETE FROM CourseSchedules WHERE courseId = '{courseId}'"

                    # NOTE: Schedules first, then the course information after
                    executeQuery(deleteFromCourseSchedules)
                    executeQuery(deleteFromCourses)

                # After deleting selected courses
                professorData = executeQuery(getProfessorsQuery)
                courseData = executeQuery(getCoursesQuery)
                scheduleData = executeQuery(getCourseSchedulesQuery)
                roomData = executeQuery(getRoomsQuery)
                current_professor = int(current_professor)
                scheduleMode = scheduleMode

            if action == "deleteUser":
                professorName = ""
                current_professor = request.form['hiddenProfessorDetails']
                deleteProfessorSchedule = f"DELETE FROM CourseSchedules WHERE professorId = {current_professor}"
                deleteHonorariumVacant = f"DELETE FROM Courses WHERE courseId = '{'HT' + current_professor}' or courseId = '{'VT' + current_professor}'"
                deleteProfessor = f"DELETE FROM Professors WHERE employeeId = {current_professor}"
                updateCourses = f"UPDATE Courses SET professorId = '' WHERE professorId = {current_professor}"

                for i, prof in enumerate(professorData):
                    if prof[0] == int(current_professor):
                    # Modify the tuple or list
                        professorData[i] = (prof[0], professorName) + prof[2:]

                executeQuery(deleteProfessorSchedule)
                executeQuery(deleteHonorariumVacant)
                executeQuery(updateCourses)
                executeQuery(deleteProfessor)
                return admin_alert.success_delete_user(current_professor, professorName)

            
            if action == "markComplete":
                current_professor = request.form['hiddenProfessorDetails']
                markCompleteQuery = f"UPDATE Professors SET employeeSchedule = 'Complete' WHERE employeeId = {current_professor}"
                executeQuery(markCompleteQuery)
                professorData = executeQuery(getProfessorsQuery)
                courseData = executeQuery(getCoursesQuery)
                scheduleData = executeQuery(getCourseSchedulesQuery)
                roomData = executeQuery(getRoomsQuery)
                return render_template('admin.html',
                    professorData=professorData,
                    courseData=courseData,
                    scheduleData=scheduleData,
                    roomData=roomData, 
                    current_professor=int(current_professor),
                    scheduleMode=1)

            if action == "markIncomplete":
                current_professor = request.form['hiddenProfessorDetails']
                markIncompleteQuery = f"UPDATE Professors SET employeeSchedule = 'Incomplete' WHERE employeeId = {current_professor}"
                executeQuery(markIncompleteQuery)
                professorData = executeQuery(getProfessorsQuery)
                courseData = executeQuery(getCoursesQuery)
                scheduleData = executeQuery(getCourseSchedulesQuery)
                roomData = executeQuery(getRoomsQuery)
                return render_template('admin.html',
                    professorData=professorData,
                    courseData=courseData,
                    scheduleData=scheduleData, 
                    roomData=roomData, 
                    current_professor=int(current_professor),
                    scheduleMode=1)

            if action == "resetSchedule":
                current_professor = request.form['hiddenProfessorDetails']
                deleteProfInScheduleQuery = f"DELETE FROM CourseSchedules WHERE professorId = {current_professor}"
                deleteCoursesFromProfQuery = f"UPDATE Courses SET professorId = NULL WHERE professorId = {current_professor}"
                executeQuery(deleteProfInScheduleQuery)
                executeQuery(deleteCoursesFromProfQuery)
                professorData = executeQuery(getProfessorsQuery)
                courseData = executeQuery(getCoursesQuery)
                scheduleData = executeQuery(getCourseSchedulesQuery)
                roomData = executeQuery(getRoomsQuery)
                return render_template('admin.html',
                    professorData=professorData,
                    courseData=courseData,
                    scheduleData=scheduleData, 
                    roomData=roomData, 
                    current_professor=int(current_professor),
                    scheduleMode=1)


            if action == "uploadExcel":
                if 'file' not in request.files:
                    return '<script>alert("File not found.");</script>'
                
                file = request.files['file']
                if file.filename == '':
                    return "No selected file."
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    executeQuery(pe.readContents(filename))
                    return admin_alert.success_subject_import()

            if action == "inquiries":
                return redirect(url_for('inquiries'))

        return render_template('admin.html',
                professorData=professorData,
                courseData=courseData,
                scheduleData=scheduleData,
                roomData=roomData,
                current_professor=int(current_professor),
                scheduleMode=scheduleMode)

# CODE BLOCK: User Inquiries
@app.route('/admin/inquiries', methods=['GET', 'POST'])
def inquiries():
    if 'userId' not in session or session['userId'] != '0000':
        return redirect(url_for("login")) # IF: Not logged in, redirect to login page
        
    else:
        getInquiriesQuery = "SELECT * FROM ProfessorInquiries"
        inquiryData = executeQuery(getInquiriesQuery)

        getProfessorsQuery = "SELECT employeeId, employeeName, employeeSchedule FROM Professors WHERE employeeId != 0000"
        professorData = executeQuery(getProfessorsQuery)

        if request.method == "POST":
            action = request.form['btn']

            if action == 'logout':
                session.pop('userId', 0)
                return redirect("/login")

            if action == 'backToAdminPage':
                return redirect("/admin")
            
            if action == 'resolveInquiry':
                currentId = int(request.form['currentId'])
                resolveQuery = f"UPDATE ProfessorInquiries SET inqStatus = 'Resolved' WHERE ID = {currentId}"
                executeQuery(resolveQuery)
                inquiryData = executeQuery(getInquiriesQuery)
                professorData = executeQuery(getProfessorsQuery)

            if action == 'denyInquiry':
                currentId = int(request.form['currentId'])
                denyQuery = f"UPDATE ProfessorInquiries SET inqStatus = 'Denied' WHERE ID = {currentId}"
                executeQuery(denyQuery)
                inquiryData = executeQuery(getInquiriesQuery)
                professorData = executeQuery(getProfessorsQuery)

        return render_template('inquiries.html',
        inquiryData=inquiryData,
        professorData=professorData)

# CODE BLOCK: Checking the file extension for import
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# CODE BLOCK: Executing the queries
def executeQuery(checkQuery, params=None):
    conn = odbc.connect(connString)
    cursor = conn.cursor()

    try:
        if params:
            cursor.execute(checkQuery, params)
        else:
            cursor.execute(checkQuery)

        if checkQuery.strip().upper().startswith("SELECT"):
            data = cursor.fetchall()
        else:
            data = None

        conn.commit()

    except odbc.Error as e:
        print(f"ERROR: Problems executing query: {e}")
        conn.rollback()
        data = None

    finally:
        cursor.close()
        conn.close()

    return data

if __name__ == '__main__':
        app.run(debug=True)