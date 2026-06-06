from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=150)),
                ('email', models.EmailField(unique=True)),
                ('pw', models.CharField(max_length=256)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('city', models.CharField(blank=True, max_length=80)),
                ('role', models.CharField(choices=[('seller', 'Seller'), ('buyer', 'Buyer')], default='buyer', max_length=10)),
                ('verified_phone', models.BooleanField(default=False)),
                ('verified_email', models.BooleanField(default=False)),
                ('cnic', models.CharField(blank=True, max_length=20)),
                ('cnic_name', models.CharField(blank=True, max_length=150)),
                ('bank_iban', models.CharField(blank=True, max_length=40)),
                ('bank_name', models.CharField(blank=True, max_length=80)),
                ('bank_title', models.CharField(blank=True, max_length=150)),
                ('jazzcash', models.CharField(blank=True, max_length=20)),
                ('easypaisa', models.CharField(blank=True, max_length=20)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={'db_table': 'ab_user'},
        ),
        migrations.CreateModel(
            name='Listing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='listings', to='core.user')),
                ('crop', models.CharField(max_length=50)),
                ('city', models.CharField(max_length=80)),
                ('market', models.CharField(blank=True, max_length=150)),
                ('price', models.PositiveIntegerField()),
                ('qty', models.PositiveIntegerField()),
                ('qty_sold', models.PositiveIntegerField(default=0)),
                ('desc', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('sold', 'Sold'), ('inactive', 'Inactive')], default='active', max_length=20)),
                ('image1', models.ImageField(blank=True, null=True, upload_to='listings/')),
                ('image2', models.ImageField(blank=True, null=True, upload_to='listings/')),
                ('image3', models.ImageField(blank=True, null=True, upload_to='listings/')),
                ('image4', models.ImageField(blank=True, null=True, upload_to='listings/')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'ab_listing', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.CharField(max_length=30, primary_key=True, serialize=False)),
                ('listing', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='core.listing')),
                ('buyer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='core.user')),
                ('seller', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sales', to='core.user')),
                ('crop', models.CharField(max_length=50)),
                ('city', models.CharField(max_length=80)),
                ('market', models.CharField(blank=True, max_length=150)),
                ('price', models.PositiveIntegerField()),
                ('qty', models.PositiveIntegerField()),
                ('total', models.PositiveIntegerField()),
                ('pay_method', models.CharField(choices=[('cod', 'Cash on Delivery'), ('jazzcash', 'JazzCash'), ('easypaisa', 'EasyPaisa'), ('bank', 'Bank Transfer')], default='cod', max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('buyer_name', models.CharField(blank=True, max_length=150)),
                ('buyer_email', models.EmailField(blank=True)),
                ('seller_name', models.CharField(blank=True, max_length=150)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'ab_order', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='core.listing')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='core.user')),
                ('order', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.order')),
                ('rating', models.PositiveSmallIntegerField()),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={'db_table': 'ab_review', 'ordering': ['-created_at']},
        ),
        migrations.AlterUniqueTogether(
            name='review',
            unique_together={('listing', 'reviewer')},
        ),
    ]
