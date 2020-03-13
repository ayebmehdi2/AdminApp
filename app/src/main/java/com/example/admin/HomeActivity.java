package com.example.admin;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.view.View;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.databinding.DataBindingUtil;

import com.bumptech.glide.Glide;
import com.example.admin.databinding.HomeBinding;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

public class HomeActivity extends AppCompatActivity {

    HomeBinding binding;
    FirebaseDatabase database;
    DatabaseReference reference;
    private String uid;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = DataBindingUtil.setContentView(this, R.layout.home);

        SharedPreferences preferences = PreferenceManager.getDefaultSharedPreferences(this);
        uid = preferences.getString("uid", null);

        database = FirebaseDatabase.getInstance();
        reference = database.getReference();

        binding.btnGenerate.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(HomeActivity.this, MainActivity.class));
            }
        });

        reference.child("ADMINS").child(uid).addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(@NonNull DataSnapshot dataSnapshot) {
                JavaUser user = dataSnapshot.getValue(JavaUser.class);
                if (user == null) return;

                if (user.getPhoto() != null){
                    try {
                        Glide.with(HomeActivity.this).load(user.getPhoto()).into(binding.photo);
                    }catch (Exception e){ }
                }else{
                    binding.photo.setImageResource(R.drawable.ic_account);
                }

                binding.name.setText(user.getName());

            }
            @Override
            public void onCancelled(@NonNull DatabaseError databaseError) { }
        });

        binding.btnStatistique.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(HomeActivity.this, StatistiqueActivity.class));
            }
        });

        binding.bar.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(HomeActivity.this, profile.class));
            }
        });

    }
}
