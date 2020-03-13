package com.example.admin;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.view.View;
import android.widget.RadioButton;
import android.widget.RadioGroup;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.databinding.DataBindingUtil;

import com.example.admin.databinding.CompleteCompteActivityBinding;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;


public class CompleteCompte extends AppCompatActivity {

    CompleteCompteActivityBinding binding;
    public static FirebaseUser user = null;
    private RadioGroup rg;
    String value = "type 1";

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = DataBindingUtil.setContentView(this, R.layout.complete_compte_activity);

        FirebaseDatabase database = FirebaseDatabase.getInstance();
        final DatabaseReference reference = database.getReference();
        SharedPreferences preferences = PreferenceManager.getDefaultSharedPreferences(this);
        final String uid = preferences.getString("uid", "");

        if (user == null) return;

        RadioGroup rg = findViewById(R.id.radioGroup1);

        RadioButton rb = findViewById(rg.getCheckedRadioButtonId());

        if (rb != null) value = rb.getText().toString();



        binding.done.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (user.getPhotoUrl() == null){
                    reference.child("ADMINS").child(uid).setValue(new JavaUser(user.getDisplayName(), "", value));
                    return;
                }


                reference.child("ADMINS").child(uid).setValue(new JavaUser(user.getDisplayName(), user.getPhotoUrl().toString(), value));

                Intent intent = new Intent(CompleteCompte.this, HomeActivity.class);
                startActivity(intent);
            }
        });



    }


}
