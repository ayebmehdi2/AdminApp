package com.example.admin;

import android.annotation.SuppressLint;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.os.AsyncTask;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.view.View;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.databinding.DataBindingUtil;

import com.example.admin.databinding.ActivityMainBinding;
import com.google.android.gms.tasks.OnFailureListener;
import com.google.android.gms.tasks.OnSuccessListener;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;
import com.google.firebase.storage.FirebaseStorage;
import com.google.firebase.storage.StorageReference;
import com.google.firebase.storage.UploadTask;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.WriterException;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.qrcode.QRCodeWriter;

import java.io.ByteArrayOutputStream;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.concurrent.ThreadLocalRandom;

public class MainActivity extends AppCompatActivity {

    private int prod = 0;
    private String name = "default";
    private int counter = 0;
    private ActivityMainBinding binding;
    private ArrayList<String> cod = new ArrayList<>();
    private String NA = "Non connue !";


    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        binding = DataBindingUtil.setContentView(this, R.layout.activity_main);

        SharedPreferences preferences = PreferenceManager.getDefaultSharedPreferences(this);
        String uid = preferences.getString("uid", null);

        FirebaseDatabase database = FirebaseDatabase.getInstance();
        DatabaseReference reference = database.getReference();

        reference.child("ADMINS").child(uid).child("name").addListenerForSingleValueEvent(new ValueEventListener() {
            @Override
            public void onDataChange(@NonNull DataSnapshot dataSnapshot) {
                String name = dataSnapshot.getValue(String.class);
                if (name != null) NA = name;
            }
            @Override
            public void onCancelled(@NonNull DatabaseError databaseError) { }
        });


        binding.genrate.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (prod == 0){
                    Toast.makeText(MainActivity.this, "You must choose product", Toast.LENGTH_LONG).show();
                    return;
                }

                @SuppressLint("SimpleDateFormat") DateFormat simple = new SimpleDateFormat("dd MMM yyyy HH:mm");
                Date result = new Date(System.currentTimeMillis());
                name = simple.format(result) + NA;
                if (!(name.length() > 0)){
                    Toast.makeText(MainActivity.this, "You must choose name", Toast.LENGTH_LONG).show();
                    return;
                }


                String num = binding.num.getText().toString();
                if (!(num.length() > 0)){
                    Toast.makeText(MainActivity.this, "You must choose number qr code", Toast.LENGTH_LONG).show();
                    return;
                }

                for (int i = 0; i < Integer.parseInt(num); i++){
                    String chifre =  String.valueOf(ThreadLocalRandom.current().nextInt(100000000, 999999999));
                    switch (prod){
                        case 1:
                            chifre = "produit1--" + chifre;
                            name = "produit1--" + name;
                            break;
                        case 2:
                            chifre = "produit2--" + chifre;
                            name = "produit2--" + name;
                            break;
                        case 3:
                            chifre = "produit3--" + chifre;
                            name = "produit3--" + name;
                            break;
                        case 4:
                            chifre = "produit4--" + chifre;
                            name = "produit4--" + name;
                            break;
                        case 5:
                            chifre = "produit5--" + chifre;
                            name = "produit5--" + name;
                            break;
                        default:
                            chifre = "0";

                    }
                    cod.add(chifre);
                }
                counter = 0;
                new AsyncT().execute(cod.get(counter));


            }
        });

    }

    @SuppressLint("StaticFieldLeak")
    class AsyncT extends AsyncTask<String, Void, Void> {

        @Override
        protected void onPreExecute() {
            super.onPreExecute();
            binding.l.setVisibility(View.VISIBLE);
        }

        @Override
        protected Void doInBackground(String... s) {
            Bitmap bmp = null;
            String content = s[0];
            if(!(content.length() > 0)) return null;
            try {
                QRCodeWriter writer = new QRCodeWriter();
                BitMatrix bitMatrix = writer.encode(content , BarcodeFormat.QR_CODE, 200, 200);
                int width = bitMatrix.getWidth();
                int height = bitMatrix.getHeight();
                bmp = Bitmap.createBitmap(width, height, Bitmap.Config.RGB_565);
                for (int x = 0; x < width; x++) {
                    for (int y = 0; y < height; y++) {
                        bmp.setPixel(x, y, bitMatrix.get(x, y) ? Color.BLACK : Color.WHITE);
                    }
                }

            } catch (WriterException e) {
                e.printStackTrace();
            }

            if (bmp != null){

                uploadBitmap(bmp, name, content);
            }

            return null;
        }



        @Override
        protected void onPostExecute(Void no) {
            counter += 1;
            if (counter < cod.size()){
                new AsyncT().execute(cod.get(counter));
            }else {
                binding.l.setVisibility(View.GONE);
                Toast.makeText(MainActivity.this, "Fin", Toast.LENGTH_LONG).show();
                binding.num.setText("");
                name = "";
                rest();
                prod = 0;
            }

        }
    }

    public void pb1(View v){
        prod = 1;
        rest();
        binding.p1.setBackgroundColor(getResources().getColor(R.color.colorAccent));
    }

    public void pb2(View v){
        prod = 2;
        rest();
        binding.p2.setBackgroundColor(getResources().getColor(R.color.colorAccent));
    }

    public void pb3(View v){
        prod = 3;
        rest();
        binding.p3.setBackgroundColor(getResources().getColor(R.color.colorAccent));
    }

    public void pb4(View v){
        prod = 4;
        rest();
        binding.p4.setBackgroundColor(getResources().getColor(R.color.colorAccent));

    }

    public void pb5(View v){
        prod = 5;
        rest();
        binding.p5.setBackgroundColor(getResources().getColor(R.color.colorAccent));
    }

    public void rest(){
        binding.p1.setBackgroundResource(0);
        binding.p2.setBackgroundResource(0);
        binding.p3.setBackgroundResource(0);
        binding.p4.setBackgroundResource(0);
        binding.p5.setBackgroundResource(0);
    }

    private void uploadBitmap(final Bitmap bitmap, String folderName, final String imageName) {

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        bitmap.compress(Bitmap.CompressFormat.JPEG, 100, baos);
        byte[] data = baos.toByteArray();

        final StorageReference ref = FirebaseStorage.getInstance().getReference().child(folderName +"/"+ imageName);
        UploadTask uploadTask = ref.putBytes(data);
        uploadTask.addOnFailureListener(new OnFailureListener() {
            @Override
            public void onFailure(@NonNull Exception e) {
                Toast.makeText(MainActivity.this, e.getMessage(), Toast.LENGTH_LONG).show();
            }
        }).addOnSuccessListener(new OnSuccessListener<UploadTask.TaskSnapshot>() {
            @Override
            public void onSuccess(UploadTask.TaskSnapshot taskSnapshot) {
                    FirebaseDatabase.getInstance().getReference().child("QrCodes/" + imageName).setValue(0);
            }
        });


    }
}
