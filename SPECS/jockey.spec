Name:		jockey
Version:	0.9.3
Release:	2%{?dist}
Summary:	Jockey driver manager

Group:		System Environment/Base
License:	GPLv2
URL:		https://launchpad.net/jockey
Source0:	jockey-kororaa-%version.tar.bz2
#Source0:	http://launchpad.net/jockey/trunk/0.9.3/+download/jockey-%version.tar.gz
#Patch0:		https://github.com/downloads/csmart/jockey/jockey-%version-kororaa.patch
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:	noarch

BuildRequires:	desktop-file-utils gettext intltool python2-devel python-distutils-extra
Requires:	dbus-python pygobject2 pyxdg python-xkit python-distutils-extra python-pycurl polkit

%description
Jockey provides a user interface and desktop integration 
for the installation and upgrade of third-party drivers.

%package	kde
Summary:	KDE frontend for Jockey
Group:		Applications/System
Requires:	jockey polkit-kde PyQt4 PyKDE4
%description 	kde
This package provides a Qt interface for Jockey.

%package	gtk
Summary:	GTK frontend for Jockey
Group:		Applications/System
Requires:	jockey polkit-gnome gdk-pixbuf gtk2
%description	gtk
This package provides a GTK interface for Jockey.

%prep
%setup -q
#%patch0 -p1

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --root %{buildroot}
mkdir -p %{buildroot}%{_var}/cache/%{name}
#mkdir -p %{buildroot}%{_datadir}/%{name}/modaliases
install data/modaliases/rpmfusion-modules.aliases %{buildroot}%{_datadir}/%{name}/modaliases/
cp -r handlers %{buildroot}%{_datadir}/%{name}/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc AUTHORS ChangeLog COPYING README.txt
%{_datadir}/doc/%{name}/README.txt
%{_bindir}/jockey-text
%{python_sitelib}
%{_datadir}/%{name}/%{name}-backend
%{_datadir}/%{name}/handlers
%{_datadir}/%{name}/modaliases
%{_datadir}/icons
%{_datadir}/locale
%{_datadir}/dbus-1
%{_datadir}/polkit-1
%{_sysconfdir}/dbus-1
%{_var}/cache/%{name}

%files gtk
%{_bindir}/jockey-gtk
%{_datadir}/%{name}/%{name}-gtk.ui
%{_datadir}/applications/jockey-gtk.desktop
%{_datadir}/autostart/jockey-gtk.desktop

%files kde
%{_bindir}/jockey-kde
%{_datadir}/%{name}/LicenseDialog.ui
%{_datadir}/%{name}/ManagerWindowKDE4.ui
%{_datadir}/%{name}/ProgressDialog.ui
%{_datadir}/applications/jockey-kde.desktop
%{_datadir}/autostart/jockey-kde.desktop
%{_datadir}/kde4/apps/jockey/jockey.notifyrc

%changelog
* Sun Aug 14 2011 Chris Smart <chris@kororaa.org> 0.9.3-2
- Initial port of oslib to yum backend. 

* Sat May 7 2011 Chris Smart <chris@kororaa.org> 0.9.3-1
- Created initial spec files from README.
