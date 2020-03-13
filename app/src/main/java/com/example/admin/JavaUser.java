package com.example.admin;

public class JavaUser  {

    private String name, photo, type;

    public JavaUser() {}

    public JavaUser(String name, String photo, String type){
        this.name = name;
        this.photo = photo;
        this.type = type;
    }


    public String getName() {
        return name;
    }

    public String getPhoto() {
        return photo;
    }

    public String getType() {
        return type;
    }

    public void setName(String name) {
        this.name = name;
    }

    public void setType(String type) {
        this.type = type;
    }

    public void setPhoto(String photo) {
        this.photo = photo;
    }
}
