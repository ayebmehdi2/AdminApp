package com.example.admin;

import android.content.SharedPreferences;
import android.os.Bundle;
import android.preference.PreferenceManager;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.databinding.DataBindingUtil;

import com.example.admin.databinding.StatistiqueBinding;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

public class StatistiqueActivity extends AppCompatActivity {

    StatistiqueBinding binding;
    FirebaseDatabase database;
    DatabaseReference reference;
    private String uid;
    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = DataBindingUtil.setContentView(this, R.layout.statistique);

        SharedPreferences preferences = PreferenceManager.getDefaultSharedPreferences(this);
        uid = preferences.getString("uid", null);

        database = FirebaseDatabase.getInstance();
        reference = database.getReference();

        reference.child("STATISTIQUE").addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(@NonNull DataSnapshot dataSnapshot) {
                Statistique user = dataSnapshot.getValue(Statistique.class);
                if (user == null) return;

                if (user.getComptes() != null) binding.comptes.setText(String.valueOf(user.getComptes()));

                Integer totalGifts = 0;
                if (user.getGift1() != null){
                    binding.g1.setText(String.valueOf(user.getGift1()));
                    totalGifts += user.getGift1();
                }
                if (user.getGift3() != null){
                    binding.g3.setText(String.valueOf(user.getGift3()));
                    totalGifts += user.getGift2();
                }
                if (user.getGift2() != null){
                    binding.g2.setText(String.valueOf(user.getGift2()));
                    totalGifts += user.getGift3();
                }
                binding.gifts.setText(String.valueOf(totalGifts));

                Integer totalProduit = 0;
                if (user.getProduit1() != null){
                    binding.p1.setText(String.valueOf(user.getProduit1()));
                    totalProduit += user.getProduit1();
                }
                if (user.getProduit2() != null){
                    binding.p2.setText(String.valueOf(user.getProduit2()));
                    totalProduit += user.getProduit2();
                }
                if (user.getProduit3() != null){
                    binding.p3.setText(String.valueOf(user.getProduit3()));
                    totalProduit += user.getProduit3();
                }
                if (user.getProduit4() != null){
                    binding.p4.setText(String.valueOf(user.getProduit4()));
                    totalProduit += user.getProduit4();
                }
                if (user.getProduit5() != null){
                    binding.p5.setText(String.valueOf(user.getProduit5()));
                    totalProduit += user.getProduit5();
                }
                binding.pT.setText(String.valueOf(totalProduit));
            }
            @Override
            public void onCancelled(@NonNull DatabaseError databaseError) { }
        });


    }

    @Override
    public void onBackPressed() {
        finish();
    }
}
