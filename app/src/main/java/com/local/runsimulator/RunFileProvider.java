package com.local.runsimulator;

import android.content.*;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import java.io.*;

/** Read-only sharing of generated files, restricted to one app-private directory. */
public final class RunFileProvider extends ContentProvider {
    private File root;
    @Override public boolean onCreate(){root=new File(getContext().getFilesDir(),"generated");return true;}
    private File resolve(Uri uri)throws FileNotFoundException{
        String name=uri.getLastPathSegment();if(name==null||name.contains("/")||name.contains("\\")||!(name.endsWith(".gpx")||name.endsWith(".fit")))throw new FileNotFoundException("Invalid file");
        File file=new File(root,name);
        try{if(!file.getCanonicalFile().getParentFile().equals(root.getCanonicalFile()))throw new FileNotFoundException("Outside root");}
        catch(IOException e){throw new FileNotFoundException("Invalid file");}
        if(!file.isFile())throw new FileNotFoundException("Not found");return file;
    }
    @Override public String getType(Uri uri){return uri.toString().endsWith(".fit")?"application/vnd.ant.fit":"application/gpx+xml";}
    @Override public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException{if(!"r".equals(mode))throw new FileNotFoundException("Read only");return ParcelFileDescriptor.open(resolve(uri),ParcelFileDescriptor.MODE_READ_ONLY);}
    @Override public Cursor query(Uri uri,String[] projection,String s,String[] a,String sort){try{
        File f=resolve(uri);String[] cols=projection==null?new String[]{"_display_name","_size"}:projection;MatrixCursor c=new MatrixCursor(cols);Object[] row=new Object[cols.length];
        for(int i=0;i<cols.length;i++)row[i]="_display_name".equals(cols[i])?f.getName():"_size".equals(cols[i])?f.length():null;c.addRow(row);return c;
    }catch(FileNotFoundException e){return null;}}
    @Override public int delete(Uri uri,String s,String[] a){throw new UnsupportedOperationException("Read only");}
    @Override public int update(Uri uri,ContentValues v,String s,String[] a){throw new UnsupportedOperationException("Read only");}
    @Override public Uri insert(Uri uri,ContentValues v){throw new UnsupportedOperationException("Read only");}
}
