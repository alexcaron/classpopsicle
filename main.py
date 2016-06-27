#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import os
import random
import logging
import time

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import memcache

import jinja2
jinja_environment = jinja2.Environment(autoescape=False,
                                       loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

# Teacher
class Teacher(db.Model):
    teacherid = db.StringProperty(required=True)
    firstname = db.StringProperty(required=True)
    lastname = db.StringProperty(required=True)
    email = db.EmailProperty()


# Course, owned by a teacher
class Course(db.Model):
    teacher = db.ReferenceProperty(Teacher, collection_name='courses')
    name = db.StringProperty(required=True)


# Student, with a "courses" object that is a list of Course object keys
class Student(db.Model):
    course = db.ReferenceProperty(Course, collection_name='students')
    firstname = db.StringProperty(required=True)
    lastname = db.StringProperty()
    tally = db.IntegerProperty()



# Convenience functions

def getRoster(course):
    students = []
    count = 0
    for stud in course.students:
        students.append(stud)
        count += 1
    return students, count


# Get teacher object for user
def getTeacher(user):
    return Teacher.gql("WHERE teacherid = :1", user.user_id()).get()


# Get courses for a teacher; returns a list
def getCourseList(teacher):
    courses = []
    for course in teacher.courses:
        courses.append(course)
    return courses

# Get course object for a course id
def getCourse(courseid):
    return Course.gql("WHERE courseid = :1", courseid).get()

# Create groups of x students
def makeGroupsOf(x,roster):
    numOfGroups = len(roster) / x
    sort = {}
    for name in roster:
        sort['name'] = random.randint(0,numOfGroups)
    return sort

# Create x groups

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, template, **params):
        t = jinja_environment.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
        


class BaseHandler(Handler):
    def get(self):
        user = users.get_current_user()
        if user:
            teacher = getTeacher(user)
            if teacher:
                courselist = getCourseList(teacher)
                coursenames = []
                for course in courselist:
                    coursenames.append((course.name, str(course.key())))
                self.render('basecamp.html', courses = coursenames, logout = users.create_logout_url('/'))
            else:
                self.redirect("/newteacher")
        else:
            self.redirect('/signin')
            

class CourseHandler(Handler):
    def get(self, url):
        user = users.get_current_user()
        if user:
            teacher = getTeacher(user)            
        else:
            self.redirect("/newteacher")

        course_key = url
        course = db.get(course_key)

        students, count = getRoster(course)
        
        names = []
        for stud in students:
            names.append((str(stud.firstname), str(stud.lastname)))
        
        self.render("course.html", name = course.name, studentlist = names, coursekey = course_key)
        
    def post(self, url):
        user = users.get_current_user()
        if user:
            teacher = getTeacher(user)
        else:
            self.redirect('/newteacher')

        course_key = url
        course = db.get(course_key)

        students, count = getRoster(course)

        names = []
        for stud in students:
            names.append((str(stud.firstname), str(stud.lastname)))

       
        stud = random.choice(students)
        try:
            stud.tally += 1
            db.put(stud)
        except TypeError:
            pass


        groups = makeGroupsOf(5,students)
    
 

        
        self.render("pop.html", name = course.name, studentlist = names, student = str(stud.firstname) + " " + str(stud.lastname), coursekey = course_key)
        


class PopHandler(Handler):
    def get(self, url):
        user = users.get_current_user()
        if user:
            teacher = getTeacher(user)
        else:
            self.redirect('/newteacher')

        course_key = url
        course = db.get(course_key)

        students, count = getRoster(course)

        names = []
        for stud in students:
            names.append((str(stud.firstname), str(stud.lastname)))

       
        stud = random.choice(students)
        try:
            stud.tally += 1
            db.put(stud)
        except TypeError:
            pass
    
 

        self.render("pop.html", name = course.name, studentlist = names, student = str(stud.firstname) + " " + str(stud.lastname), coursekey = course_key)
        


class NewTeacherHandler(Handler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.render('newteacherform.html', email = user.email())
        else:
            self.redirect('/signin')

    def post(self):
        firstname = self.request.get("firstname")
        lastname = self.request.get("lastname")
        email = self.request.get("email")
        teacherid = users.get_current_user().user_id()      # teacherid matches user id
        
        newteacher = Teacher(teacherid=teacherid, firstname=firstname,
                             lastname=lastname, email=email)
        newteacher.put()

        self.redirect('/newcourse')


class NewCourseHandler(Handler):
    def get(self):
        user = users.get_current_user()
        if user:
            teacher = getTeacher(user)
            self.render('newcourseform.html', message = "Let's get you started by adding your first class.")

    def post(self):
        user = users.get_current_user()
        if user:
            teacher = getTeacher(user)
            print teacher

        coursename = self.request.get("coursename")
        classlist = self.request.get("classlist")

        newcourse = Course(teacher=teacher, name=coursename)
        newcourse.put()
        
        course_key = newcourse.key()
        
        names = classlist.splitlines()
        for name in names:
            name = name.split()
            newstudent = Student(course=newcourse, firstname=name[0], lastname=name[1], tally=0)
            newstudent.put()

        self.redirect("/course/home/" + str(course_key))
        


class SignInHandler(Handler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.redirect("/")

        else:
            self.render('signin.html', url = users.create_login_url('/'))
                        
 
 
app = webapp2.WSGIApplication([
    ('/', BaseHandler),
    ('/newteacher', NewTeacherHandler),
    ('/newcourse', NewCourseHandler),
    ('/signin', SignInHandler),
    ('/course/home/(\S+)', CourseHandler),
    ('/course/pop/(\S+)', PopHandler)
], debug=True)
